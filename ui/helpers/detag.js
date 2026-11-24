'use strict'

module.exports = (html) => html && html.replace(/<[^>]+>/g, '')
