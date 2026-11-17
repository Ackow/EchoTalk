// Release 正文中仅使用「更新亮点」标题下的顶层列表，避免展示安装说明等内容。
function extractHighlights(body) {
  const lines = String(body || '').split(/\r?\n/)
  const start = lines.findIndex((line) => /^\s{0,3}#{1,6}\s+更新亮点\s*#*\s*$/.test(line))
  if (start < 0) return []
  const headingLevel = lines[start].trimStart().match(/^#+/)[0].length
  const highlights = []
  for (const line of lines.slice(start + 1)) {
    const heading = line.match(/^\s{0,3}(#{1,6})\s+/)
    if (heading && heading[1].length <= headingLevel) break
    const item = line.match(/^\s{0,3}[-*+]\s+(.+?)\s*$/)
    if (item) highlights.push(item[1].replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/[*_`]/g, '').slice(0, 200))
    if (highlights.length === 5) break
  }
  return highlights
}

module.exports = { extractHighlights }
