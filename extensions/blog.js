'use strict'

// Builds the blog front page and the tag and category archives from the post headers.
// A post is any page below pages/YYYY/MM/DD/ with :page-date:, :page-tags: and :page-categories: attributes.

const POST_PATH = /^\d{4}\/\d{2}\/\d{2}\//

const slugify = (name) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

const splitList = (value) => (value ? value.split(',').map((it) => it.trim()).filter(Boolean) : [])

function readPost (file) {
  const header = {}
  const lines = file.contents.toString().split('\n')
  const title = lines[0].replace(/^=\s+/, '')
  for (const line of lines.slice(1)) {
    if (!line.trim()) break
    const m = line.match(/^:([\w-]+):\s*(.*)$/)
    if (m) header[m[1]] = m[2]
  }
  return {
    path: file.src.relative,
    title,
    date: header['page-date'] || '',
    description: header.description || '',
    teaser: header['page-teaser'] || '',
    categories: splitList(header['page-categories']),
    tags: splitList(header['page-tags']),
  }
}

const byDateDesc = (a, b) => b.date.localeCompare(a.date) || a.title.localeCompare(b.title)

const escapeLinkText = (text) => text.replace(/]/g, '\\]')

function renderPost (post) {
  const lines = ['[.post]', '--', '[.post-date]', post.date, '', '[.post-title]', 'xref:' + post.path + '[' + escapeLinkText(post.title) + ']', '']
  if (post.description) lines.push('[.post-desc]', 'pass:c[' + post.description.replace(/]/g, '\\]') + ']', '')
  if (post.tags.length) {
    lines.push('[.post-tags]', post.tags.map((tag) => 'xref:tag/' + slugify(tag) + '.adoc[' + escapeLinkText(tag) + ']').join(' '), '')
  }
  if (post.teaser) lines.push('[.post-teaser]', 'image::' + post.teaser + '[alt=""]', '')
  lines.push('--', '')
  return lines.join('\n') + '\n'
}

// Each group of posts (a year, or a whole tag or category) is one zone block, styled in the UI.
function renderZone (heading, posts) {
  const label = heading ? '[discrete]\n== ' + heading + '\n\n' : ''
  return '[.zone]\n====\n' + label + posts.map(renderPost).join('') + '====\n\n'
}

function renderPosts (posts, groupByYear) {
  if (!groupByYear) return renderZone(null, posts)
  const years = new Map()
  for (const post of posts) {
    const year = post.date.slice(0, 4)
    if (!years.has(year)) years.set(year, [])
    years.get(year).push(post)
  }
  return [...years.entries()].map(([year, group]) => renderZone(year, group)).join('')
}

function groupBy (posts, key) {
  const groups = new Map()
  for (const post of posts) {
    for (const name of post[key]) {
      if (!groups.has(name)) groups.set(name, [])
      groups.get(name).push(post)
    }
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
}

function renderTopics (kind, groups) {
  return groups.map(([name, posts]) => 'xref:' + kind + '/' + slugify(name) + '.adoc[' + escapeLinkText(name) + '] (' + posts.length + ')').join(' ')
}

module.exports.register = function () {
  this.once('contentClassified', ({ contentCatalog }) => {
    const files = contentCatalog.findBy({ component: 'ROOT', module: 'ROOT', family: 'page' })
    const posts = files.filter((file) => POST_PATH.test(file.src.relative)).map(readPost).sort(byDateDesc)
    const { component, version, module } = files[0].src
    const addPage = (relative, adoc) => {
      contentCatalog.addFile({ contents: Buffer.from(adoc), src: { component, version, module, family: 'page', relative } })
    }
    const categories = groupBy(posts, 'categories')
    const tags = groupBy(posts, 'tags')

    addPage('index.adoc', [
      '= Pragmatic Application Security',
      ':description: Thoughts on Secure Software Development',
      '',
      renderPosts(posts, true),
      '[discrete]',
      '== Topics',
      '',
      '[.topics]',
      '*Categories:* ' + renderTopics('category', categories),
      '',
      '[.topics]',
      '*Tags:* ' + renderTopics('tag', tags),
      '',
    ].join('\n'))

    for (const [name, group] of categories) {
      addPage('category/' + slugify(name) + '.adoc', '= Category: ' + name + '\n\n' + renderPosts(group, false))
    }
    for (const [name, group] of tags) {
      addPage('tag/' + slugify(name) + '.adoc', '= Tag: ' + name + '\n\n' + renderPosts(group, false))
    }
  })
}
