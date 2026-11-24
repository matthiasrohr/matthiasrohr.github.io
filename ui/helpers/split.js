'use strict'

module.exports = (value) => (typeof value === 'string' ? value.split(',').map((it) => it.trim()).filter(Boolean) : [])
