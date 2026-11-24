#!/usr/bin/env python3
"""One-time import of published WordPress posts from an UpdraftPlus SQL dump into Antora pages.

Usage: wp_import.py DUMP.sql CONTENT_DIR [UPLOADS_DIR ...]
  CONTENT_DIR  the Antora start_path, e.g. content
  UPLOADS_DIR  extracted wp-content/uploads directories, searched in the given order; the images and
               files the posts reference (including each post's featured image as teaser) are copied
               to CONTENT_DIR/modules/ROOT/images and .../attachments (images only with a matching
               image signature)

Writes CONTENT_DIR/modules/ROOT/pages/YYYY/MM/DD/<slug>.adoc for every published post.
Existing files with the same name are overwritten, so do not re-run after editing posts by hand.
Needs pandoc and BeautifulSoup. The dump is only read; nothing from the users table is touched.
"""
import collections
import html
import os
import re
import shutil
import subprocess
import sys

from bs4 import BeautifulSoup, Comment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqldump  # noqa: E402

SITE_HOSTS = re.compile(r'^https?://(?:www\.)?(?:blog2?\.secodis\.com|matthiasrohr\.de)(?P<path>/.*)?$', re.I)
POST_PATH = re.compile(r'^/\d{4}/\d{2}/\d{2}/(?P<slug>[^/]+)/?(?:#.*)?$')
UPLOAD_PATH = re.compile(r'^/wp-content/uploads/(?P<file>.+)$')
IMAGE_MAGIC = {'.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff', '.gif': b'GIF8', '.webp': b'RIFF'}
BLOCK_OPEN = r'<(?:table|ul|ol|pre|blockquote|h[1-6]|div|figure|hr|p)\b'


def clean_text(s):
    for _ in range(3):
        s = html.unescape(s)
    return re.sub(r'\s+', ' ', s.replace(' ', ' ')).strip()


def autop(text):
    """Approximation of WordPress wpautop for posts written in the classic editor."""
    text = text.replace('\r\n', '\n')
    keep = []

    def stash(m):
        keep.append(m.group(0))
        return '\n\n@@PRE%d@@\n\n' % (len(keep) - 1)

    text = re.sub(r'<pre\b.*?</pre>', stash, text, flags=re.S | re.I)
    text = re.sub(r'(<(?:table|ul|ol|blockquote|h[1-6]|div|figure|hr)\b[^>]*>)', r'\n\n\1', text, flags=re.I)
    text = re.sub(r'(</(?:table|ul|ol|blockquote|h[1-6]|div|figure)>)', r'\1\n\n', text, flags=re.I)
    out = []
    for part in re.split(r'\n\s*\n', text):
        part = part.strip('\n')
        if not part.strip():
            continue
        if re.match(BLOCK_OPEN, part.strip(), re.I) or part.strip().startswith('@@PRE'):
            out.append(part)
        else:
            out.append('<p>' + part.replace('\n', '<br>\n') + '</p>')
    result = '\n\n'.join(out)
    return re.sub(r'@@PRE(\d+)@@', lambda m: keep[int(m.group(1))], result)


class Importer:
    def __init__(self, slug_to_path):
        self.slug_to_path = slug_to_path
        self.unresolved_links = collections.defaultdict(set)
        self.images = collections.defaultdict(set)
        self.attachments = collections.defaultdict(set)
        self.files = collections.defaultdict(set)

    def rewrite_href(self, href, slug):
        m = SITE_HOSTS.match(href)
        if not m:
            return href
        path = m.group('path') or '/'
        pm = POST_PATH.match(path)
        if pm and pm.group('slug') in self.slug_to_path:
            frag = '#' + href.split('#', 1)[1] if '#' in href else ''
            return 'xref-marker:' + self.slug_to_path[pm.group('slug')] + frag
        um = UPLOAD_PATH.match(path)
        if um:
            self.attachments[slug].add(um.group('file'))
            return 'xref-marker:attachment$' + um.group('file')
        self.unresolved_links[slug].add(href)
        return href

    def prepare(self, content, slug):
        if '<!-- wp:' not in content:
            content = autop(content)
        soup = BeautifulSoup(content, 'html.parser')
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            c.extract()
        for t in soup.find_all(['span', 'font', 'div']):
            t.unwrap()
        fragments = {a['href'][1:] for a in soup.find_all('a', href=True) if a['href'].startswith('#')}
        for t in soup.find_all(True):
            keep = {k: v for k, v in t.attrs.items()
                    if (k == 'href' and t.name == 'a') or (k in ('src', 'alt') and t.name == 'img')
                    or (k in ('colspan', 'rowspan') and t.name in ('td', 'th'))
                    or (k == 'id' and v in fragments)}
            t.attrs = keep
        for img in soup.find_all('img'):
            img['alt'] = clean_text(img.get('alt', ''))
            m = SITE_HOSTS.match(img.get('src', ''))
            um = UPLOAD_PATH.match(m.group('path') or '') if m else None
            if um:
                img['src'] = um.group('file')
                self.images[slug].add(um.group('file'))
            elif img.get('src'):
                self.files[slug].add(img['src'])
        for a in soup.find_all('a', href=True):
            href = a['href']
            if a.find('img') and not a.get_text(strip=True):
                a.unwrap()
                continue
            if not href.startswith('#'):
                a['href'] = self.rewrite_href(href, slug)
        for a in soup.find_all('a', href=True):
            if a.get_text(strip=True) == '↩︎' or a.get_text(strip=True) == '↩':
                a.decompose()
        for p in soup.find_all('p'):
            if p.find('img'):
                self.split_images(soup, p)
        for p in soup.find_all('p'):
            if not p.get_text(strip=True) and not p.find('img'):
                p.decompose()
        heads = [int(h.name[1]) for h in soup.find_all(re.compile(r'^h[1-6]$'))]
        if heads and min(heads) != 2:
            shift = 2 - min(heads)
            for h in soup.find_all(re.compile(r'^h[1-6]$')):
                h.name = 'h%d' % max(1, min(6, int(h.name[1]) + shift))
        return soup

    @staticmethod
    def split_images(soup, p):
        """An image inside running text becomes its own paragraph, so it is rendered as a block."""
        groups, cur = [], []
        for node in list(p.children):
            if getattr(node, 'name', None) == 'img':
                groups += [cur, [node]]
                cur = []
            elif getattr(node, 'name', None) == 'br' and not cur:
                continue
            else:
                cur.append(node)
        groups.append(cur)
        for nodes in groups:
            if not nodes or (all(getattr(n, 'name', None) == 'br' or not str(n).strip() for n in nodes)):
                continue
            q = soup.new_tag('p')
            for n in nodes:
                q.append(n.extract())
            p.insert_before(q)
        p.decompose()

    def to_asciidoc(self, soup):
        p = subprocess.run(['pandoc', '-f', 'html', '-t', 'asciidoc', '--wrap=none'],
                           input=str(soup), capture_output=True, text=True, check=True)
        out = p.stdout.replace(' ', ' ')
        out = re.sub(r'(?:link:)?(?:\+\+)?xref-marker:([^\[+]+?)(?:\+\+)?\[', r'xref:\1[', out)
        out = re.sub(r'\n{3,}', '\n\n', out).strip()
        blocks = []
        for b in out.split('\n\n'):
            if b.startswith('image:') and b.endswith(']'):
                b = re.sub(r'\s*\+?\n\s*', ' ', b)
                b = re.sub(r'^image::?', 'image::', b).replace('[ ', '[')
            blocks.append(b)
        return '\n\n'.join(blocks) + '\n'


def description_of(soup):
    for p in soup.find_all('p'):
        text = clean_text(p.get_text())
        if len(text) >= 40:
            text = re.sub(r'[{}]', '', text)
            if len(text) <= 200:
                return text
            cut = text[:200].rsplit(' ', 1)[0].rstrip(' ,;:.-')
            return cut + '…'
    return ''


def find_upload(uploads_dirs, rel):
    for uploads_dir in uploads_dirs:
        root = os.path.realpath(uploads_dir)
        src = os.path.realpath(os.path.join(root, rel))
        if src.startswith(root + os.sep) and os.path.isfile(src):
            return src
    return None


def pick_teaser(meta, post_id, available):
    """Featured image of a post: the smallest size that is at least 640 px wide, else the largest."""
    thumb = meta.get(post_id, {}).get('_thumbnail_id')
    attachment = meta.get(int(thumb), {}) if thumb else {}
    original = attachment.get('_wp_attached_file')
    if not original:
        return None
    info = attachment.get('_wp_attachment_metadata') or ''
    folder = os.path.dirname(original)
    candidates = []
    top = re.search(r's:5:"width";i:(\d+);s:6:"height";i:\d+;s:4:"file";s:\d+:"([^"]+)"', info)
    if top:
        candidates.append((int(top.group(1)), original))
    for name, width in re.findall(r's:4:"file";s:\d+:"([^"]+)";s:5:"width";i:(\d+);', info):
        candidates.append((int(width), os.path.join(folder, name)))
    if not candidates:
        candidates = [(0, original)]
    ordered = sorted(c for c in candidates if c[0] >= 640) + sorted((c for c in candidates if c[0] < 640), reverse=True)
    for _, rel in ordered:
        if available(rel):
            return rel
    return ordered[0][1]


def copy_uploads(uploads_dirs, target_dir, wanted, images):
    """Copy referenced files out of untrusted uploads trees; images must carry a matching signature."""
    for rel in sorted(wanted):
        src = find_upload(uploads_dirs, rel)
        if not src:
            continue
        if images:
            magic = IMAGE_MAGIC.get(os.path.splitext(rel)[1].lower())
            with open(src, 'rb') as f:
                if not magic or not f.read(len(magic)).startswith(magic):
                    print('skipped, not an image:', rel)
                    continue
        dest = os.path.join(target_dir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)


def main(dump, content_dir, *uploads_dirs):
    sql = open(dump, encoding='utf-8').read()
    posts = [p for p in sqldump.table(sql, 'wp_posts') if p['post_type'] == 'post' and p['post_status'] == 'publish']
    terms = {t['term_id']: t for t in sqldump.table(sql, 'wp_terms')}
    tax = {t['term_taxonomy_id']: t for t in sqldump.table(sql, 'wp_term_taxonomy')}
    rel = collections.defaultdict(list)
    for r in sqldump.table(sql, 'wp_term_relationships'):
        t = tax.get(r['term_taxonomy_id'])
        if t:
            rel[r['object_id']].append((t['taxonomy'], clean_text(terms[t['term_id']]['name'])))

    def page_path(p):
        y, m, d = p['post_date'][:10].split('-')
        return '%s/%s/%s/%s.adoc' % (y, m, d, p['post_name'])

    meta = collections.defaultdict(dict)
    for m in sqldump.table(sql, 'wp_postmeta'):
        meta[m['post_id']][m['meta_key']] = m['meta_value']
    module_dir = os.path.join(content_dir, 'modules', 'ROOT')
    images_dir = os.path.join(module_dir, 'images')
    attachments_dir = os.path.join(module_dir, 'attachments')

    def available(rel):
        return find_upload(uploads_dirs, rel) or os.path.isfile(os.path.join(images_dir, rel))

    imp = Importer({p['post_name']: page_path(p) for p in posts})
    pages_dir = os.path.join(module_dir, 'pages')
    teasers = {}
    for p in sorted(posts, key=lambda p: p['post_date']):
        slug = p['post_name']
        soup = imp.prepare(p['post_content'], slug)
        body = imp.to_asciidoc(soup)
        cats = [n for t, n in rel[p['ID']] if t == 'category' and n != 'Uncategorized']
        tags = [n for t, n in rel[p['ID']] if t == 'post_tag']
        header = ['= ' + clean_text(p['post_title']), ':page-date: ' + p['post_date'][:10]]
        if cats:
            header.append(':page-categories: ' + ', '.join(sorted(cats)))
        if tags:
            header.append(':page-tags: ' + ', '.join(sorted(tags)))
        teaser = pick_teaser(meta, p['ID'], available)
        if teaser:
            teasers[slug] = teaser
            header.append(':page-teaser: ' + teaser)
        desc = description_of(soup)
        if desc:
            header.append(':description: ' + desc)
        out = os.path.join(pages_dir, page_path(p))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write('\n'.join(header) + '\n\n' + body)
    wanted = {i for s in imp.images.values() for i in s} | set(teasers.values())
    attachments = {a for s in imp.attachments.values() for a in s}
    if uploads_dirs:
        copy_uploads(uploads_dirs, images_dir, wanted, images=True)
        copy_uploads(uploads_dirs, attachments_dir, attachments, images=False)
    print('posts written:', len(posts))
    print('images referenced (incl. teasers):', len(wanted), '| posts with teaser:', len(teasers), 'of', len(posts))
    print('\nREFERENCED IMAGES NOT FOUND IN', images_dir)
    for rel in sorted(wanted):
        if not os.path.isfile(os.path.join(images_dir, rel)):
            print(' ', rel)
    for rel in sorted(attachments):
        if not os.path.isfile(os.path.join(attachments_dir, rel)):
            print('  (attachment)', rel)
    print('\nUNRESOLVED INTERNAL LINKS')
    for slug, links in sorted(imp.unresolved_links.items()):
        for l in sorted(links):
            print(' ', slug, '->', l)
    print('\nNON-IMAGE FILES / EXTERNAL IMAGES LINKED FROM THE OLD SITE')
    for slug, links in sorted(imp.files.items()):
        for l in sorted(links):
            print(' ', slug, '->', l)


if __name__ == '__main__':
    main(*sys.argv[1:])
