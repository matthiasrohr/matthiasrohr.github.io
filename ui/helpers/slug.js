'use strict'

// Must match slugify() in extensions/blog.js, which generates the tag and category pages.
module.exports = (name) => String(name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
