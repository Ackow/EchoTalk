/**
 * 场景包清单自动生成器
 *
 * 扫描 public/scenes/ 目录下的所有 .zip 文件，
 * 从每个 zip 包内提取 scene_config.json，
 * 自动生成 public/packages.json。
 *
 * 用法: node scripts/generate-manifest.js
 */

const fs = require('fs')
const path = require('path')
const AdmZip = require('adm-zip')

const SCENES_DIR = path.resolve(__dirname, '..', 'public', 'scenes')
const OUTPUT_FILE = path.resolve(__dirname, '..', 'public', 'packages.json')

// ── 分类 → 标签映射 ──
const CATEGORY_TAG_MAP = {
  interview: ['interview'],
  meeting: ['business'],
  ordering: ['food'],
  business: ['business'],
  travel: ['travel'],
  food: ['food'],
  daily: ['daily'],
  tech: ['tech'],
  culture: ['culture'],
  academic: ['academic'],
}

// ── 分类 → emoji 映射 ──
const CATEGORY_EMOJI_MAP = {
  interview: '💼',
  meeting: '🏢',
  ordering: '🍽️',
  business: '📊',
  travel: '✈️',
  food: '🍴',
  daily: '💬',
  tech: '💻',
  culture: '🎭',
  academic: '🎓',
}

function scanScenePackages() {
  if (!fs.existsSync(SCENES_DIR)) {
    console.log('[generate-manifest] public/scenes/ 目录不存在，创建空清单')
    return []
  }

  const files = fs.readdirSync(SCENES_DIR)
  const zipFiles = files.filter(f => f.toLowerCase().endsWith('.zip'))

  console.log(`[generate-manifest] 扫描到 ${zipFiles.length} 个场景包:`)

  const packages = []

  for (const zipFile of zipFiles) {
    const zipPath = path.join(SCENES_DIR, zipFile)
    console.log(`  📦 ${zipFile}`)

    try {
      const zip = new AdmZip(zipPath)
      const configEntry = zip.getEntry('scene_config.json')

      if (!configEntry) {
        console.warn(`    ⚠ 缺少 scene_config.json，跳过`)
        continue
      }

      const config = JSON.parse(configEntry.getData().toString('utf-8'))

      // 从 scene_config.json 提取字段
      const category = config.category || 'custom'
      const tags = CATEGORY_TAG_MAP[category] || [category]
      const emoji = CATEGORY_EMOJI_MAP[category] || '📦'

      const pkg = {
        id: config.id || path.basename(zipFile, '.zip'),
        emoji,
        title: config.name || config.id || path.basename(zipFile, '.zip'),
        author: config.author || '社区贡献',
        desc: config.description || '暂无描述',
        tags,
        rating: '--',
        downloads: '--',
        featured: false,
        downloadUrl: `/scenes/${zipFile}`,
      }

      packages.push(pkg)
      console.log(`    ✓ ${pkg.title} (${pkg.id})`)
    } catch (err) {
      console.error(`    ✗ 读取失败: ${err.message}`)
    }
  }

  return packages
}

// ── 主流程 ──
const packages = scanScenePackages()

// 内置包放前面 (id 为 interview / meeting / ordering 的)
const builtinIds = ['interview', 'meeting', 'ordering']
packages.sort((a, b) => {
  const aBuiltin = builtinIds.includes(a.id)
  const bBuiltin = builtinIds.includes(b.id)
  if (aBuiltin && !bBuiltin) return -1
  if (!aBuiltin && bBuiltin) return 1
  return 0
})

// 标记内置包
for (const pkg of packages) {
  if (builtinIds.includes(pkg.id)) {
    pkg.featured = true
    pkg.author = 'EchoTalk Team'
    pkg.downloads = '内置'
    pkg.rating = pkg.id === 'interview' ? '4.9' : pkg.id === 'meeting' ? '4.8' : '4.7'
  }
}

fs.writeFileSync(OUTPUT_FILE, JSON.stringify(packages, null, 2), 'utf-8')
console.log(`\n[generate-manifest] ✅ 已生成 packages.json (${packages.length} 个包)`)
