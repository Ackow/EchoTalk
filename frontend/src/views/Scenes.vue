<template>
  <!-- 场景探索：搜索 / 分类 / 来源筛选 / 场景卡（作者·封面） / 详情弹窗 / 导入导出与互动 -->
  <section v-show="trainingPhase !== 'chat'" class="scenes-page">
    <!-- 工具行：大选择（对话/辩论） + 来源类别 + 创建/导入 -->
    <div class="scenes-toolbar">
      <div class="toolbar-left">
        <div class="explore-mode-tabs compact" role="tablist" aria-label="场景探索板块">
          <button
            type="button"
            role="tab"
            class="explore-mode-tab"
            :class="{ active: exploreMode === 'conversation' }"
            :aria-selected="exploreMode === 'conversation'"
            @click="exploreMode = 'conversation'"
          >
            <AppIcon name="messages" :size="14" />
            <span>对话场景</span>
            <span class="mode-count">{{ countFor('all') }}</span>
          </button>
          <button
            type="button"
            role="tab"
            class="explore-mode-tab"
            :class="{ active: exploreMode === 'debate' }"
            :aria-selected="exploreMode === 'debate'"
            @click="exploreMode = 'debate'"
          >
            <AppIcon name="users" :size="14" />
            <span>多角色对话</span>
            <span class="mode-count">{{ debateCountFor('all') }}</span>
          </button>
        </div>

        <AppTabs
          v-if="exploreMode === 'conversation'"
          v-model="filter"
          :options="filters.map((t) => ({ value: t.key, label: t.label, count: countFor(t.key) }))"
          aria-label="场景来源筛选"
        />
        <AppTabs
          v-else
          v-model="debateSourceFilter"
          :options="debateSourceFilters.map((t) => ({ value: t.key, label: t.label, count: debateCountFor(t.key) }))"
          aria-label="多角色来源筛选"
        />
      </div>
      <div class="toolbar-actions">
        <template v-if="exploreMode === 'conversation'">
          <button class="ghost-button" type="button" @click="pickImport">
            <AppIcon name="download" :size="14" />导入场景包
          </button>
          <button class="primary-button slim" type="button" @click="goCreate">
            <AppIcon name="plus" :size="14" />新建场景
          </button>
          <input ref="importInput" type="file" accept=".zip" class="hidden-input" @change="handleImportFile" />
        </template>
        <template v-else>
          <button class="ghost-button" type="button" @click="pickDebateImport">
            <AppIcon name="download" :size="14" />导入多角色包
          </button>
          <button class="primary-button slim" type="button" @click="router.push({ name: 'debate-create' })">
            <AppIcon name="plus" :size="14" />新建多角色场景
          </button>
          <input ref="debateImportInput" type="file" accept=".zip,.json" class="hidden-input" @change="handleDebateImportFile" />
        </template>
      </div>
    </div>

    <!-- 筛选行：分类 chips + 排序 + 搜索框 -->
    <div class="filter-row">
      <div v-if="exploreMode === 'conversation'" class="cat-chips" role="group" aria-label="场景分类筛选">
        <button
          v-for="cat in CATEGORIES"
          :key="cat.key"
          type="button"
          class="cat-chip"
          :class="{ active: category === cat.key }"
          @click="category = cat.key"
        >{{ cat.label }}</button>
      </div>
      <div v-else class="cat-chips" role="group" aria-label="多角色分类筛选">
        <button
          v-for="cat in DEBATE_CATEGORIES"
          :key="cat.key"
          type="button"
          class="cat-chip"
          :class="{ active: debateCategory === cat.key }"
          @click="debateCategory = cat.key"
        >{{ cat.label }}</button>
      </div>

      <div class="filter-right">
        <AppSelect
          v-if="exploreMode === 'conversation'"
          v-model="sortBy"
          :options="SORT_OPTIONS"
          label="排序"
          aria-label="排序方式"
        />
        <AppSelect
          v-else
          v-model="debateSortBy"
          :options="SORT_OPTIONS"
          label="排序"
          aria-label="多角色排序方式"
        />
        <label v-if="exploreMode === 'conversation'" class="search-box">
          <AppIcon name="search" :size="14" />
          <input v-model="keyword" type="search" placeholder="搜索场景名称、描述或标签" />
          <button v-if="keyword" class="search-clear" type="button" aria-label="清空搜索" @click="keyword = ''">
            <AppIcon name="x" :size="12" />
          </button>
        </label>
        <label v-else class="search-box">
          <AppIcon name="search" :size="14" />
          <input v-model="debateKeyword" type="search" placeholder="搜索多角色场景、议题或角色设定" />
          <button v-if="debateKeyword" class="search-clear" type="button" aria-label="清空搜索" @click="debateKeyword = ''">
            <AppIcon name="x" :size="12" />
          </button>
        </label>
      </div>
    </div>

    <template v-if="exploreMode === 'conversation'">

    <!-- 卡片网格：入场 stagger 动画 -->
    <div v-if="!initializing" class="scene-grid" key="grid">
      <article
        v-for="(scene, index) in pagedItems"
        :key="scene.id"
        class="scene-card"
        :style="{ animationDelay: `${Math.min(index, 8) * 45}ms` }"
        @click="openDetail(scene)"
      >
        <SceneCover :scene="scene" :category-label="categoryLabel(scene.category)" />
        <div class="card-body">
          <header class="card-head">
            <span class="mode-chip" :data-mode="scene.mode">
              <AppIcon :name="modeIcon(scene.mode)" :size="13" />{{ modeLabel(scene.mode) }}
            </span>
            <span class="source-chip" :class="scene.source === 'builtin' ? 'builtin' : scene.status">
              <AppIcon :name="scene.source === 'builtin' ? 'check' : scene.status === 'published' ? 'globe' : 'lock'" :size="12" />
              {{ sourceLabel(scene) }}
            </span>
            <div class="card-menu-anchor">
              <button class="menu-trigger" type="button" :aria-label="`场景 ${scene.name} 的更多操作`" @click.stop="toggleMenu(scene)">
                <AppIcon name="dots" :size="15" />
              </button>
              <transition name="pop">
                <div v-if="menuFor === scene.id" class="card-menu" role="menu" @click.stop>
                  <button v-if="canEdit(scene)" class="menu-item" type="button" @click="goEdit(scene)">
                    <AppIcon name="pencil" :size="13" />编辑
                  </button>
                  <button v-if="session.token" class="menu-item" type="button" @click="doDuplicate(scene)">
                    <AppIcon name="copy" :size="13" />复制为我的场景
                  </button>
                  <button class="menu-item" type="button" @click="doExport(scene)">
                    <AppIcon name="upload" :size="13" />导出 ZIP
                  </button>
                  <button v-if="canEdit(scene)" class="menu-item" type="button" @click="doPublishToggle(scene)">
                    <AppIcon :name="scene.status === 'published' ? 'lock' : 'send'" :size="13" />
                    {{ scene.status === 'published' ? '取消发布' : '发布到社区' }}
                  </button>
                  <div v-if="canEdit(scene)" class="menu-divider" aria-hidden="true"></div>
                  <button v-if="canEdit(scene)" class="menu-item danger" type="button" @click.stop="menuFor = null; deleteTarget = scene">
                    <AppIcon name="trash" :size="13" />删除
                  </button>
                </div>
              </transition>
            </div>
          </header>

          <p class="card-desc">{{ scene.description || '作者还没有填写场景描述。' }}</p>

          <div v-if="scene.tags.length" class="card-tags">
            <span v-for="tag in scene.tags.slice(0, 3)" :key="tag" class="tag-chip">{{ tag }}</span>
          </div>

          <!-- 作者行：官方场景显示品牌 Logo，其余使用 UserAvatar（无自定义头像时自动回落首字母） + 署名 + 难度 -->
          <div class="card-author">
            <img v-if="isOfficialAuthor(scene)" class="avatar-logo" :src="brandImage" alt="EchoTalk" />
            <UserAvatar v-else :user="authorUser(scene)" :size="22" />
            <span class="author-name">{{ scene.author_name || 'EchoTalk 官方' }}</span>
            <span v-if="scene.difficulty" class="diff-chip" :class="diffClass(scene.difficulty)">{{ diffLabel(scene.difficulty) }}</span>
          </div>

          <footer class="card-foot">
            <div class="card-meta">
              <span v-if="scene.objective_count" class="meta-item">
                <AppIcon name="target" :size="12" />{{ scene.objective_count }} 个目标
              </span>
              <span v-if="scene.knowledge_count" class="meta-item">
                <AppIcon name="book-open" :size="12" />{{ scene.knowledge_count }} 份资料
              </span>
            </div>
            <div class="card-stats">
              <button
                class="stat-button like"
                type="button"
                :class="{ on: scene.stats?.liked }"
                :aria-pressed="scene.stats?.liked"
                :title="session.token ? '点赞' : '登录后可点赞'"
                @click.stop="toggleLike(scene)"
              >
                <AppIcon name="heart" :size="13" />{{ scene.stats?.likes || 0 }}
              </button>
              <button
                class="stat-button fav"
                type="button"
                :class="{ on: scene.stats?.favorited }"
                :aria-pressed="scene.stats?.favorited"
                :title="session.token ? '收藏并加入训练台' : '登录后可收藏'"
                @click.stop="toggleFavorite(scene)"
              >
                <AppIcon name="star" :size="13" />{{ scene.stats?.favorites || 0 }}
              </button>
              <span class="stat-plain" title="累计训练量"><AppIcon name="target" :size="12" />{{ scene.stats?.plays || 0 }}</span>
            </div>
          </footer>
        </div>
      </article>

      <!-- 空状态：无匹配结果时引导调整筛选 -->
      <div v-if="!filteredItems.length" class="scenes-empty">
        <div class="empty-icon"><AppIcon name="package" :size="22" /></div>
        <h3>{{ emptyTitle }}</h3>
        <p>{{ emptyDesc }}</p>
        <button v-if="filter === 'mine' && !keyword && category === 'all'" class="primary-button slim" type="button" @click="goCreate">
          <AppIcon name="plus" :size="14" />创建第一个场景
        </button>
      </div>
    </div>

    <!-- 分页栏：常驻底部，展示总数与页码（单页时上下页按钮禁用） -->
    <nav v-if="!initializing && filteredItems.length" class="pagination" aria-label="场景分页">
      <span class="page-info">共 {{ filteredItems.length }} 个场景 · 第 {{ page }} / {{ totalPages }} 页</span>
      <button class="page-btn" type="button" :disabled="page === 1" @click="page -= 1">
        <AppIcon name="chevron-left" :size="14" />上一页
      </button>
      <button
        v-for="p in totalPages"
        :key="p"
        class="page-btn page-num"
        :class="{ active: p === page }"
        type="button"
        :aria-current="p === page ? 'page' : undefined"
        @click="page = p"
      >{{ p }}</button>
      <button class="page-btn" type="button" :disabled="page === totalPages" @click="page += 1">
        下一页<AppIcon name="arrow-right" :size="14" />
      </button>
    </nav>
    </template>

    <!-- 板块二：多角色对话场景 -->
    <template v-else>
      <div v-if="!initializing" class="scene-grid debate-explore-grid">
        <article
          v-for="(topic, index) in pagedDebateTopics"
          :key="topic.id"
          class="scene-card"
          :style="{ animationDelay: `${Math.min(index, 8) * 45}ms` }"
          @click="openDebateDetail(topic)"
        >
          <SceneCover :scene="debateCoverModel(topic)" :category-label="topic.categoryLabel || (topic.sceneType === 'panel' ? '多人对话' : '正反辩论')" />
          <div class="card-body">
            <header class="card-head">
              <span class="mode-chip" :data-mode="topic.sceneType || 'debate'">
                <AppIcon :name="topic.sceneType === 'panel' ? 'users' : 'sparkles'" :size="13" />
                {{ topic.sceneType === 'panel' ? '多人对话' : '正反辩论' }}
              </span>
              <span class="source-chip" :class="topic.isBuiltin !== false ? 'builtin' : topic.status">
                <AppIcon :name="topic.isBuiltin !== false ? 'check' : topic.status === 'published' ? 'globe' : 'lock'" :size="12" />
                {{ topic.isBuiltin !== false ? '内置' : topic.status === 'published' ? '已发布' : '本地' }}
              </span>
              <div class="card-menu-anchor">
                <button class="menu-trigger" type="button" :aria-label="`多角色场景 ${topic.titleZh} 的更多操作`" @click.stop="toggleDebateMenu(topic)">
                  <AppIcon name="dots" :size="15" />
                </button>
                <transition name="pop">
                  <div v-if="debateMenuFor === topic.id" class="card-menu" role="menu" @click.stop>
                    <button v-if="canEditDebate(topic)" class="menu-item" type="button" @click="goEditDebate(topic)">
                      <AppIcon name="pencil" :size="13" />编辑
                    </button>
                    <button v-if="session.token" class="menu-item" type="button" @click="doDuplicateDebate(topic)">
                      <AppIcon name="copy" :size="13" />复制为我的场景
                    </button>
                    <button class="menu-item" type="button" @click="doExportDebate(topic)">
                      <AppIcon name="upload" :size="13" />导出 ZIP
                    </button>
                    <button v-if="canEditDebate(topic)" class="menu-item" type="button" @click="doPublishDebateToggle(topic)">
                      <AppIcon :name="topic.status === 'published' ? 'lock' : 'send'" :size="13" />
                      {{ topic.status === 'published' ? '取消发布' : '发布到社区' }}
                    </button>
                    <div v-if="canEditDebate(topic)" class="menu-divider" aria-hidden="true"></div>
                    <button v-if="canEditDebate(topic)" class="menu-item danger" type="button" @click.stop="askDeleteDebate(topic)">
                      <AppIcon name="trash" :size="13" />删除
                    </button>
                  </div>
                </transition>
              </div>
            </header>

            <p class="card-desc debate-motion-en">{{ topic.motionEn }}</p>

            <div class="card-tags">
              <span
                v-for="expr in (topic.keyExpressions || []).slice(0, 3)"
                :key="expr"
                class="tag-chip"
              >{{ expr }}</span>
              <template v-if="!(topic.keyExpressions && topic.keyExpressions.length)">
                <span v-if="topic.sceneType === 'panel' && topic.userRoleLabel" class="tag-chip">我的身份 · {{ topic.userRoleLabel }}</span>
                <span v-else class="tag-chip">正方 · {{ topic.proSummary }}</span>
              </template>
            </div>

            <div class="card-author">
              <img v-if="topic.isBuiltin !== false" class="avatar-logo" :src="brandImage" alt="EchoTalk" />
              <UserAvatar v-else :user="{ username: topic.authorName || '学习者' }" :size="22" />
              <span class="author-name">{{ topic.authorName || 'EchoTalk 官方' }}</span>
              <span class="diff-chip" :class="debateDiffClass(topic.difficulty)">{{ topic.difficultyLabel || '进阶' }}</span>
            </div>

            <footer class="card-foot">
              <div class="card-meta">
                <span class="meta-item">
                  <AppIcon name="clock" :size="12" />{{ topic.duration || '8 分钟' }}
                </span>
                <span class="meta-item">
                  <AppIcon :name="topic.roles?.length > 1 ? 'users' : 'user'" :size="12" />
                  {{ topic.roles?.length ? topic.roles.map((r) => r.name).join(' · ') : (topic.opponentName || 'Sonia') }}
                </span>
              </div>
              <div class="card-stats">
                <button
                  class="stat-button like"
                  type="button"
                  :class="{ on: topic.stats?.liked }"
                  :aria-pressed="topic.stats?.liked"
                  :title="session.token ? '点赞' : '登录后可点赞'"
                  @click.stop="toggleDebateLike(topic)"
                >
                  <AppIcon name="heart" :size="13" />{{ topic.stats?.likes || 0 }}
                </button>
                <button
                  class="stat-button fav"
                  type="button"
                  :class="{ on: topic.stats?.favorited }"
                  :aria-pressed="topic.stats?.favorited"
                  :title="session.token ? '收藏并加入训练台' : '登录后可收藏'"
                  @click.stop="toggleDebateFavorite(topic)"
                >
                  <AppIcon name="star" :size="13" />{{ topic.stats?.favorites || 0 }}
                </button>
                <span class="stat-plain" title="累计训练量"><AppIcon name="target" :size="12" />{{ topic.stats?.plays || 0 }}</span>
              </div>
            </footer>
          </div>
        </article>
        <div v-if="!filteredDebateTopics.length" class="scenes-empty">
          <div class="empty-icon"><AppIcon name="users" :size="22" /></div>
          <h3>没有匹配的多角色场景</h3>
          <p>尝试更换关键词或前往多角色对话工作台新建自定义场景。</p>
        </div>
      </div>

      <nav v-if="!initializing && filteredDebateTopics.length" class="pagination" aria-label="多角色场景分页">
        <span class="page-info">共 {{ filteredDebateTopics.length }} 个场景 · 第 {{ debatePage }} / {{ debateTotalPages }} 页</span>
        <button class="page-btn" type="button" :disabled="debatePage === 1" @click="debatePage -= 1">
          <AppIcon name="chevron-left" :size="14" />上一页
        </button>
        <button
          v-for="p in debateTotalPages"
          :key="p"
          class="page-btn page-num"
          :class="{ active: p === debatePage }"
          type="button"
          :aria-current="p === debatePage ? 'page' : undefined"
          @click="debatePage = p"
        >{{ p }}</button>
        <button class="page-btn" type="button" :disabled="debatePage === debateTotalPages" @click="debatePage += 1">
          下一页<AppIcon name="arrow-right" :size="14" />
        </button>
      </nav>
    </template>

    <!-- 全局骨架：首屏加载（独立条件，避免与分页器的 v-if 串联） -->
    <div v-if="initializing" class="scene-grid" aria-busy="true" aria-label="正在加载场景">
      <div v-for="n in 4" :key="n" class="scene-card skeleton">
        <div class="sk-line w40"></div>
        <div class="sk-line w80"></div>
        <div class="sk-line w60"></div>
        <div class="sk-line w70"></div>
      </div>
    </div>

    <!-- 场景详情弹窗：点击卡片打开，展示完整包信息与操作 -->
    <transition name="fade">
      <div v-if="detail" class="modal-backdrop" @click.self="detail = null">
        <div class="detail-card" role="dialog" aria-modal="true" :aria-label="`场景 ${detail.name} 详情`">
          <button class="detail-close" type="button" aria-label="关闭详情" @click="detail = null">
            <AppIcon name="x" :size="15" />
          </button>
          <div v-if="detail.cover_path" class="detail-cover">
            <img :src="coverUrl(detail.id)" alt="" @error="detail.cover_path = null" />
          </div>
          <div class="detail-content">
            <header class="detail-head">
              <h3>{{ detail.name }}</h3>
              <div class="detail-chips">
                <span class="mode-chip" :data-mode="detail.mode">
                  <AppIcon :name="modeIcon(detail.mode)" :size="13" />{{ modeLabel(detail.mode) }}
                </span>
                <span v-if="detail.difficulty" class="diff-chip" :class="diffClass(detail.difficulty)">{{ diffLabel(detail.difficulty) }}</span>
                <span class="cat-chip-static">{{ categoryLabel(detail.category) }}</span>
                <span class="source-chip" :class="detail.source === 'builtin' ? 'builtin' : detail.status">
                  <AppIcon :name="detail.source === 'builtin' ? 'check' : detail.status === 'published' ? 'globe' : 'lock'" :size="12" />
                  {{ sourceLabel(detail) }}
                </span>
              </div>
              <div class="card-author">
                <img v-if="isOfficialAuthor(detail)" class="avatar-logo" :src="brandImage" alt="EchoTalk" />
                <UserAvatar v-else :user="authorUser(detail)" :size="22" />
                <span class="author-name">{{ detail.author_name || 'EchoTalk 官方' }}</span>
                <span class="author-date" v-if="detail.created_at">创建于 {{ formatDate(detail.created_at) }}</span>
              </div>
            </header>

            <p class="detail-desc">{{ detail.description || '作者还没有填写场景描述。' }}</p>

            <div v-if="detail.tags?.length" class="card-tags">
              <span v-for="tag in detail.tags" :key="tag" class="tag-chip">{{ tag }}</span>
            </div>

            <!-- 角色列表：完整包加载后显示 -->
            <div v-if="detail.package?.roles?.length" class="detail-section">
              <h4>你在和谁对话</h4>
              <div class="role-grid">
                <div v-for="role in detail.package.roles" :key="role.id" class="role-item">
                  <span class="role-name">{{ role.display_name }}</span>
                  <span v-if="role.title" class="role-title">{{ role.title }}</span>
                </div>
              </div>
            </div>

            <!-- 对话流程 -->
            <div v-if="detail.package?.stages?.length" class="detail-section">
              <h4>对话流程（{{ detail.package.stages.length }}）</h4>
              <ul class="objective-list">
                <li v-for="stage in detail.package.stages" :key="stage.id">
                  <AppIcon name="arrow-right" :size="13" />{{ stage.name }}
                </li>
              </ul>
            </div>

            <!-- 训练目标 -->
            <div v-if="detail.package?.objectives?.length" class="detail-section">
              <h4>训练目标（{{ detail.package.objectives.length }}）</h4>
              <ul class="objective-list">
                <li v-for="objective in detail.package.objectives" :key="objective.id">
                  <AppIcon name="target" :size="13" />{{ objective.label }}
                </li>
              </ul>
            </div>

            <!-- 启用工具 -->
            <div v-if="detail.package?.tools?.allowed?.length" class="detail-section">
              <h4>启用工具（{{ detail.package.tools.allowed.length }}）</h4>
              <div class="card-tags">
                <span v-for="toolId in detail.package.tools.allowed" :key="toolId" class="tag-chip">{{ toolLabel(toolId) }}</span>
              </div>
            </div>

            <!-- 知识资料 -->
            <div v-if="detail.documents?.length" class="detail-section">
              <h4>场景资料（{{ detail.documents.length }}）</h4>
              <ul class="doc-brief">
                <li v-for="doc in detail.documents" :key="doc.id">
                  <AppIcon name="file-text" :size="13" />{{ doc.filename }}
                  <span class="doc-chunks">{{ doc.chunk_count }} 块</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- 底部操作栏：滚动容器外层，固定贴底不随内容滚动 -->
          <div v-if="favRequiredHint && !detail.stats?.favorited" class="detail-fav-hint" role="alert">
            <AppIcon name="star" :size="14" />
            <span>请先点击下方「收藏」按钮收藏该场景，然后再开始训练。</span>
          </div>
          <footer class="detail-foot">
            <div class="detail-stats">
              <span class="stat-plain" title="喜欢"><AppIcon name="heart" :size="13" />{{ detail.stats?.likes || 0 }}</span>
              <span class="stat-plain" title="收藏"><AppIcon name="star" :size="13" />{{ detail.stats?.favorites || 0 }}</span>
              <span class="stat-plain" title="训练量"><AppIcon name="target" :size="13" />{{ detail.stats?.plays || 0 }}</span>
            </div>
            <div class="detail-actions">
              <button
                class="ghost-button"
                :class="{ 'fav-active': detail.stats?.favorited }"
                type="button"
                @click="toggleFavorite(detail)"
              >
                <AppIcon name="star" :size="13" />{{ detail.stats?.favorited ? '已收藏' : '收藏' }}
              </button>
              <button v-if="canEdit(detail)" class="ghost-button" type="button" @click="goEdit(detail); detail = null">
                <AppIcon name="pencil" :size="13" />编辑
              </button>
              <button v-if="session.token" class="ghost-button" type="button" @click="doDuplicate(detail); detail = null">
                <AppIcon name="copy" :size="13" />复制
              </button>
              <button class="ghost-button" type="button" @click="doExport(detail)">
                <AppIcon name="upload" :size="13" />导出
              </button>
              <button class="primary-button slim" type="button" @click="startTraining(detail)">
                <AppIcon name="messages" :size="13" />开始训练
              </button>
            </div>
          </footer>
        </div>
      </div>
    </transition>

    <!-- 多角色详情弹窗 -->
    <transition name="fade">
      <div v-if="debateDetail" class="modal-backdrop" @click.self="debateDetail = null">
        <div class="detail-card" role="dialog" aria-modal="true" :aria-label="`${debateDetail.titleZh} 详情`">
          <button class="detail-close" type="button" aria-label="关闭详情" @click="debateDetail = null">
            <AppIcon name="x" :size="15" />
          </button>
          <div v-if="debateDetail.coverUrl" class="detail-cover">
            <img :src="debateCoverUrl(debateDetail.id)" alt="" @error="debateDetail.coverUrl = ''" />
          </div>
          <div class="detail-content">
            <header class="detail-head">
              <h3>{{ debateDetail.titleZh }}</h3>
              <div class="detail-chips">
                <span class="mode-chip" :data-mode="debateDetail.sceneType || 'debate'">
                  <AppIcon :name="debateDetail.sceneType === 'panel' ? 'users' : 'sparkles'" :size="13" />
                  {{ debateDetail.sceneType === 'panel' ? '多人对话 / 群面' : '正反辩论对抗' }}
                </span>
                <span class="diff-chip" :class="debateDiffClass(debateDetail.difficulty)">{{ debateDetail.difficultyLabel || '进阶' }}</span>
                <span class="cat-chip-static">{{ debateDetail.categoryLabel || '科技伦理' }}</span>
                <span class="source-chip" :class="debateDetail.isBuiltin !== false ? 'builtin' : debateDetail.status">
                  <AppIcon :name="debateDetail.isBuiltin !== false ? 'check' : debateDetail.status === 'published' ? 'globe' : 'lock'" :size="12" />
                  {{ debateDetail.isBuiltin !== false ? '内置' : debateDetail.status === 'published' ? '已发布' : '本地' }}
                </span>
              </div>
              <div class="card-author">
                <img v-if="debateDetail.isBuiltin !== false" class="avatar-logo" :src="brandImage" alt="EchoTalk" />
                <UserAvatar v-else :user="{ username: debateDetail.authorName || '学习者' }" :size="22" />
                <span class="author-name">{{ debateDetail.authorName || 'EchoTalk 官方' }}</span>
                <span class="author-date" v-if="debateDetail.createdAt">创建于 {{ formatDate(debateDetail.createdAt) }}</span>
              </div>
            </header>

            <p class="detail-desc">{{ debateDetail.motionEn }}</p>
            <p v-if="debateDetail.backgroundContext" class="detail-desc muted-ctx">{{ debateDetail.backgroundContext }}</p>

            <div v-if="debateDetail.keyExpressions?.length" class="card-tags">
              <span v-for="expr in debateDetail.keyExpressions" :key="expr" class="tag-chip">{{ expr }}</span>
            </div>

            <div class="detail-section">
              <h4>{{ debateDetail.sceneType === 'panel' ? '参与身份与讨论焦点' : '正反方核心立场' }}</h4>
              <div v-if="debateDetail.sceneType === 'panel'" class="role-grid">
                <div class="role-item">
                  <span class="role-name">我的身份</span>
                  <span class="role-title">{{ debateDetail.userRoleLabel || 'Candidate' }}</span>
                </div>
                <div class="role-item">
                  <span class="role-name">核心目标</span>
                  <span class="role-title">{{ debateDetail.proSummary || debateDetail.motionEn }}</span>
                </div>
                <div v-if="debateDetail.conSummary" class="role-item">
                  <span class="role-name">重点考察 / 压力点</span>
                  <span class="role-title">{{ debateDetail.conSummary }}</span>
                </div>
              </div>
              <div v-else class="role-grid">
                <div class="role-item">
                  <span class="role-name">正方立场</span>
                  <span class="role-title">{{ debateDetail.proSummary || '支持该辩题核心主张' }}</span>
                </div>
                <div class="role-item">
                  <span class="role-name">反方立场</span>
                  <span class="role-title">{{ debateDetail.conSummary || '质疑并反驳该辩题主张' }}</span>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <h4>
                {{
                  debateDetail.roles?.length
                    ? `AI 多角色席位（${debateDetail.roles.length} 位）`
                    : 'AI 对手设定'
                }}
              </h4>
              <div v-if="debateDetail.roles?.length" class="role-grid">
                <div v-for="role in debateDetail.roles" :key="role.key || role.name" class="role-item">
                  <span class="role-name">{{ role.name }}</span>
                  <span class="role-title">{{ role.title || '对话角色' }}{{ role.focus ? ` · ${role.focus}` : '' }}</span>
                </div>
              </div>
              <div v-else class="role-grid">
                <div class="role-item">
                  <span class="role-name">{{ debateDetail.opponentName || 'Sonia' }}</span>
                  <span class="role-title">{{ debateDetail.opponentTitle || '对手辩手' }}</span>
                </div>
                <div v-if="debateDetail.opponentPersona" class="role-item">
                  <span class="role-name">交锋风格</span>
                  <span class="role-title">{{ debateDetail.opponentPersona }}</span>
                </div>
              </div>
            </div>

            <div v-if="debateDetail.stages?.length" class="detail-section">
              <h4>对话流程（{{ debateDetail.stages.length }}）</h4>
              <ul class="objective-list">
                <li v-for="stage in debateDetail.stages" :key="stage.id">
                  <AppIcon name="arrow-right" :size="13" />{{ stage.shortTag ? `${stage.shortTag} · ${stage.label}` : stage.label }}
                </li>
              </ul>
            </div>

            <div v-if="debateDetail.tools?.length" class="detail-section">
              <h4>启用工具（{{ debateDetail.tools.length }}）</h4>
              <div class="card-tags">
                <span v-for="toolId in debateDetail.tools" :key="toolId" class="tag-chip">{{ toolLabel(toolId) }}</span>
              </div>
            </div>

            <div v-if="debateDetail.knowledgeDocIds?.length" class="detail-section">
              <h4>场景资料（{{ debateDetail.knowledgeDocIds.length }}）</h4>
              <ul class="doc-brief">
                <li>
                  <AppIcon name="file-text" :size="13" />已关联 {{ debateDetail.knowledgeDocIds.length }} 份个人知识库文档
                </li>
              </ul>
            </div>
          </div>

          <div v-if="favRequiredHint && !debateDetail.stats?.favorited" class="detail-fav-hint" role="alert">
            <AppIcon name="star" :size="14" />
            <span>请先点击下方「收藏」按钮收藏该场景，然后再开始训练。</span>
          </div>
          <footer class="detail-foot">
            <div class="detail-stats">
              <span class="stat-plain" title="喜欢"><AppIcon name="heart" :size="13" />{{ debateDetail.stats?.likes || 0 }}</span>
              <span class="stat-plain" title="收藏"><AppIcon name="star" :size="13" />{{ debateDetail.stats?.favorites || 0 }}</span>
              <span class="stat-plain" title="训练量"><AppIcon name="target" :size="13" />{{ debateDetail.stats?.plays || 0 }}</span>
            </div>
            <div class="detail-actions">
              <button
                class="ghost-button"
                :class="{ 'fav-active': debateDetail.stats?.favorited }"
                type="button"
                @click="toggleDebateFavorite(debateDetail)"
              >
                <AppIcon name="star" :size="13" />{{ debateDetail.stats?.favorited ? '已收藏' : '收藏' }}
              </button>
              <button v-if="canEditDebate(debateDetail)" class="ghost-button" type="button" @click="goEditDebate(debateDetail); debateDetail = null">
                <AppIcon name="pencil" :size="13" />编辑
              </button>
              <button v-if="session.token" class="ghost-button" type="button" @click="doDuplicateDebate(debateDetail); debateDetail = null">
                <AppIcon name="copy" :size="13" />复制
              </button>
              <button class="ghost-button" type="button" @click="doExportDebate(debateDetail)">
                <AppIcon name="upload" :size="13" />导出
              </button>
              <button class="primary-button slim" type="button" @click="openDebateTopic(debateDetail)">
                <AppIcon :name="debateDetail.sceneType === 'panel' ? 'users' : 'sparkles'" :size="13" />开始训练
              </button>
            </div>
          </footer>
        </div>
      </div>
    </transition>

    <!-- 删除确认弹窗 -->
    <transition name="fade">
      <div v-if="deleteTarget" class="modal-backdrop" @click.self="deleteTarget = null">
        <div class="modal-card" role="alertdialog" aria-modal="true" aria-label="删除确认">
          <div class="modal-icon danger"><AppIcon name="trash" :size="18" /></div>
          <h3>删除「{{ deleteTarget._isDebate ? deleteTarget.titleZh : deleteTarget.name }}」？</h3>
          <p>{{ deleteTarget._isDebate ? '该多角色场景的配置会被移除；已开始的训练记录保留快照，此操作无法撤销。' : '场景的配置与知识资料会被移除；已开始的训练记录保留快照，此操作无法撤销。' }}</p>
          <div class="modal-actions">
            <button class="ghost-button" type="button" @click="deleteTarget = null">取消</button>
            <button class="danger-button" type="button" @click="confirmDeleteTarget">确认删除</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 导入冲突弹窗：覆盖 / 改名 / 取消 -->
    <transition name="fade">
      <div v-if="conflict" class="modal-backdrop" @click.self="conflict = null">
        <div class="modal-card" role="alertdialog" aria-modal="true" aria-label="导入冲突">
          <div class="modal-icon"><AppIcon name="package" :size="18" /></div>
          <h3>场景 ID 已存在</h3>
          <p>{{ conflict.message }}</p>
          <div class="modal-actions">
            <button class="ghost-button" type="button" @click="conflict = null">取消</button>
            <button class="ghost-button" type="button" @click="resolveImport('rename')">改名导入</button>
            <button class="primary-button slim" type="button" @click="resolveImport('overwrite')">覆盖现有</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 轻提示 -->
    <transition name="toast">
      <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    </transition>
  </section>
  <Practice
    v-if="activeTrainingScene"
    :embedded-scene="activeTrainingScene"
    @phase="trainingPhase = $event"
    @exit="activeTrainingScene = null; trainingPhase = 'select'"
  />
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import brandImage from '../assets/echotalk-brand.png'
import UserAvatar from '../components/UserAvatar.vue'
import AppIcon from '../components/AppIcon.vue'
import AppSelect from '../components/AppSelect.vue'
import AppTabs from '../components/AppTabs.vue'
import Practice from './Practice.vue'
import SceneCover from '../components/scene/SceneCover.vue'
import { session } from '../auth/session'
import { usePageLoading } from '../app/loading'
import {
  coverUrl, deleteScene, duplicateScene, exportScene, favoriteScene, getScene, importScene,
  likeScene, listScenes, publishScene, unpublishScene,
} from '../api/scenes'
import {
  debateCoverUrl,
  deleteDebateTopic,
  duplicateDebateTopic,
  exportDebateTopic,
  favoriteDebateTopic,
  importDebateTopic,
  likeDebateTopic,
  listDebateTopics,
  publishDebateTopic,
  unpublishDebateTopic,
} from '../api/debate'

// 场景模式 → 图标与中文标签（卡片左上角徽标）
const MODE_META = {
  conversation: { icon: 'messages', label: '对话' },
  interview: { icon: 'briefcase', label: '面试' },
  debate: { icon: 'users', label: '多角色' },
}
const modeIcon = (mode) => MODE_META[mode]?.icon || 'messages'
const modeLabel = (mode) => MODE_META[mode]?.label || mode

// 场景分类（与创建向导一致）
const CATEGORIES = [
  { key: 'all', label: '全部' },
  { key: 'daily', label: '日常沟通' },
  { key: 'business', label: '职场沟通' },
  { key: 'career', label: '求职训练' },
  { key: 'academic', label: '学术场景' },
  { key: 'custom', label: '自定义' },
]
const categoryLabel = (key) => CATEGORIES.find((cat) => cat.key === key)?.label || key
// 封面色调与图标已收敛到 SceneCover 组件，两个页面共用一套映射

const filters = [
  { key: 'all', label: '全部' },
  { key: 'builtin', label: '内置' },
  { key: 'community', label: '社区' },
  { key: 'favorited', label: '收藏' },
  { key: 'mine', label: '我的' },
]

const route = useRoute()
const router = useRouter()
const exploreMode = ref(route.query?.tab === 'debate' ? 'debate' : 'conversation')
watch(() => route.query?.tab, (tab) => {
  if (tab === 'debate') exploreMode.value = 'debate'
  else if (tab === 'conversation') exploreMode.value = 'conversation'
})
const items = ref([])
const debateTopics = ref([])
const debateSourceFilter = ref('all')
const debateMenuFor = ref(null)
const debateSourceFilters = [
  { key: 'all', label: '全部' },
  { key: 'builtin', label: '内置' },
  { key: 'community', label: '社区' },
  { key: 'favorited', label: '收藏' },
  { key: 'mine', label: '我的' },
]
function matchesDebateSource(topic, key) {
  if (key === 'builtin') return topic.isBuiltin !== false
  if (key === 'mine') return Boolean(topic.isMine)
  if (key === 'community') return topic.isBuiltin === false && !topic.isMine && topic.status === 'published'
  if (key === 'favorited') return Boolean(topic.stats?.favorited)
  return topic.isBuiltin !== false || topic.status === 'published'
}
const debateCountFor = (key) => debateTopics.value.filter((t) => matchesDebateSource(t, key)).length
const debateCategory = ref('all')
const debateKeyword = ref('')
const debateSortBy = ref('hot')
const DEBATE_CATEGORIES = [
  { key: 'all', label: '全部' },
  { key: 'tech', label: '科技伦理' },
  { key: 'workplace', label: '职场文化' },
  { key: 'education', label: '教育成长' },
  { key: 'society', label: '社会生活' },
]
const debateHotScore = (t) => (t.stats?.likes || 0) * 3 + (t.stats?.favorites || 0) * 2 + (t.stats?.plays || 0)
const debateCreatedTs = (t) => {
  const ts = new Date(t.createdAt || t.created_at || 0).getTime()
  return Number.isFinite(ts) ? ts : 0
}
const filteredDebateTopics = computed(() => {
  const q = debateKeyword.value.trim().toLowerCase()
  const list = debateTopics.value.filter((t) => {
    if (!matchesDebateSource(t, debateSourceFilter.value)) return false
    if (debateCategory.value !== 'all' && t.category !== debateCategory.value) return false
    if (!q) return true
    return [
      t.titleZh,
      t.motionEn,
      t.userRoleLabel,
      t.opponentName,
      t.opponentTitle,
      t.proSummary,
      t.conSummary,
      ...(t.roles || []).flatMap((r) => [r.name, r.title]),
    ]
      .filter(Boolean)
      .some((f) => String(f).toLowerCase().includes(q))
  })
  if (debateSortBy.value === 'hot') {
    return [...list].sort((a, b) => debateHotScore(b) - debateHotScore(a) || debateCreatedTs(b) - debateCreatedTs(a))
  }
  if (debateSortBy.value === 'plays') {
    return [...list].sort((a, b) => (b.stats?.plays || 0) - (a.stats?.plays || 0) || debateHotScore(b) - debateHotScore(a))
  }
  if (debateSortBy.value === 'newest') {
    return [...list].sort((a, b) => debateCreatedTs(b) - debateCreatedTs(a))
  }
  if (debateSortBy.value === 'favorites') {
    return [...list].sort((a, b) => (b.stats?.favorites || 0) - (a.stats?.favorites || 0) || debateHotScore(b) - debateHotScore(a))
  }
  if (debateSortBy.value === 'difficulty') {
    const order = { beginner: 0, intermediate: 1, advanced: 2 }
    return [...list].sort((a, b) => (order[a.difficulty] ?? 1) - (order[b.difficulty] ?? 1))
  }
  return list
})
function toggleDebateMenu(topic) {
  debateMenuFor.value = debateMenuFor.value === topic.id ? null : topic.id
}
function goEditDebate(topic) {
  debateMenuFor.value = null
  router.push({ name: 'debate-edit', params: { id: topic.id } })
}
async function toggleDebateLike(topic) {
  if (!session.token) return notify('点赞需要先登录，点击左下角账户卡片登录。')
  try {
    const { data } = await likeDebateTopic(topic.id)
    topic.stats = { ...(topic.stats || {}), liked: data.liked, likes: data.likes }
  } catch (err) {
    notify(err?.message || '点赞失败')
  }
}
async function toggleDebateFavorite(topic) {
  if (!session.token) return notify('收藏需要先登录，点击左下角账户卡片登录。')
  try {
    const { data } = await favoriteDebateTopic(topic.id)
    topic.stats = { ...(topic.stats || {}), favorited: data.favorited, favorites: data.favorites }
  } catch (err) {
    notify(err?.message || '收藏失败')
  }
}
async function doPublishDebateToggle(topic) {
  debateMenuFor.value = null
  try {
    const fn = topic.status === 'published' ? unpublishDebateTopic : publishDebateTopic
    const { data } = await fn(topic.id)
    if (data?.topic) Object.assign(topic, data.topic)
    notify(topic.status === 'published' ? '已发布到社区，其他学习者可以查看与收藏' : '已设为仅自己可见')
  } catch (err) {
    notify(err?.message || '操作失败')
  }
}
async function doDuplicateDebate(topic) {
  debateMenuFor.value = null
  try {
    const { data } = await duplicateDebateTopic(topic.id)
    if (data?.topic) {
      debateTopics.value.unshift(data.topic)
      notify(`已复制为「${data.topic.titleZh}」`)
    }
  } catch (err) {
    notify(err?.message || '复制失败')
  }
}
function askDeleteDebate(topic) {
  debateMenuFor.value = null
  deleteTarget.value = { ...topic, _isDebate: true }
}
async function doDeleteDebate(topic) {
  debateMenuFor.value = null
  try {
    await deleteDebateTopic(topic.id)
    debateTopics.value = debateTopics.value.filter((t) => t.id !== topic.id)
    if (debateDetail.value?.id === topic.id) debateDetail.value = null
    notify(`已删除「${topic.titleZh}」`)
  } catch (err) {
    notify(err?.message || '删除失败')
  }
}
async function doExportDebate(topic) {
  debateMenuFor.value = null
  try {
    await exportDebateTopic(topic.id)
    notify(`已导出「${topic.titleZh}」`)
  } catch (err) {
    notify(err?.message || '导出失败')
  }
}
const debateImportInput = ref(null)
function pickDebateImport() {
  if (!session.token) return notify('导入多角色包需要先登录，点击左下角账户卡片登录。')
  debateImportInput.value?.click()
}
async function handleDebateImportFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const { data } = await importDebateTopic(file)
    if (data?.topic) {
      debateTopics.value.unshift(data.topic)
      debateSourceFilter.value = 'mine'
      notify(`导入成功：${data.topic.titleZh}`)
    }
  } catch (err) {
    notify(err?.message || '导入多角色包失败')
  }
}
const debateDetail = ref(null)
const favRequiredHint = ref(false)

function canEditDebate(topic) {
  return Boolean(session.user && topic && topic.isBuiltin === false && topic.isMine)
}

function toolLabel(id) {
  return {
    search_knowledge: '知识检索',
    get_hint: '表达提示',
    rebuttal_hint: '回复与表达提示',
    lookup_word: '词汇查询',
    calculate_expression: '精确计算',
    add_review_task: '加入复习',
    judge_score: '实时评估评分',
    fact_check: '事实核查追问',
    set_state: '状态更新',
    append_state_item: '列表追加',
    mark_objective: '目标达成标记',
  }[id] || id
}

function openDebateDetail(topic) {
  debateMenuFor.value = null
  debateDetail.value = topic
}

function openDebateTopic(topic) {
  if (!topic?.id) return
  if (!session.token) return notify('开始训练需要先登录，点击左下角账户卡片登录。')
  if (!topic.stats?.favorited) {
    favRequiredHint.value = true
    return notify('请先收藏该多角色场景，然后再开始训练。')
  }
  favRequiredHint.value = false
  debateDetail.value = null
  router.push({ name: 'debate', query: { topic: topic.id } })
}
const DEBATE_COVER_CAT_MAP = {
  tech: 'academic',
  workplace: 'business',
  education: 'campus',
  society: 'daily',
}
function debateCoverModel(topic) {
  return {
    id: topic.id,
    name: topic.titleZh,
    category: DEBATE_COVER_CAT_MAP[topic.category] || 'academic',
    cover_image_url: topic.coverUrl ? debateCoverUrl(topic.id) : '',
  }
}
function debateDiffClass(diff) {
  return { beginner: 'easy', intermediate: 'normal', advanced: 'hard' }[diff] || 'normal'
}
const initializing = ref(true)
const filter = ref('all')
const category = ref('all')
const keyword = ref('')
const menuFor = ref(null) // 当前展开菜单的场景 id
const deleteTarget = ref(null) // 删除确认目标
const conflict = ref(null) // { file, message }：导入 ID 冲突弹窗
const detail = ref(null) // 详情弹窗数据（初始为卡片摘要，完整包异步并入）
watch([detail, debateDetail], () => {
  favRequiredHint.value = false
})
const toast = ref('')
let toastTimer = null

const notify = (message) => {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2600)
}

// 来源筛选：all=内置+已发布；mine=本人（含私有）；community=他人已发布；favorited=我收藏的
const isMine = (scene) => session.user && scene.source !== 'builtin' && scene.author_id === session.user.id
const matchesSource = (scene, key) => {
  if (key === 'builtin') return scene.source === 'builtin'
  if (key === 'mine') return isMine(scene)
  if (key === 'community') return scene.source !== 'builtin' && !isMine(scene)
  if (key === 'favorited') return !!scene.stats?.favorited
  return scene.source === 'builtin' || scene.status === 'published'
}
// 每个 tab 的计数独立计算（修复：此前所有 tab 都显示当前筛选的数量）
const countFor = (key) => items.value.filter((scene) => matchesSource(scene, key)).length
const matchesKeyword = (scene) => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return true
  return [scene.name, scene.description, ...(scene.tags || [])]
    .filter(Boolean)
    .some((field) => String(field).toLowerCase().includes(text))
}
const filteredItems = computed(() =>
  items.value.filter((scene) =>
    matchesSource(scene, filter.value)
    && (category.value === 'all' || scene.category === category.value)
    && matchesKeyword(scene),
  ),
)

// 排序：热度为喜欢/收藏/训练量的加权综合；同分按创建时间新者优先
const hotScore = (scene) =>
  (scene.stats?.likes || 0) * 3 + (scene.stats?.favorites || 0) * 2 + (scene.stats?.plays || 0)
const createdTs = (scene) => {
  const ts = new Date(scene.created_at || scene.updated_at || 0).getTime()
  return Number.isFinite(ts) ? ts : 0
}
const DIFF_ORDER = { entry: 0, easy: 1, normal: 2, hard: 3, expert: 4 }
const SORTERS = {
  hot: { label: '热度最高', fn: (a, b) => hotScore(b) - hotScore(a) || createdTs(b) - createdTs(a) },
  plays: { label: '训练最多', fn: (a, b) => (b.stats?.plays || 0) - (a.stats?.plays || 0) || hotScore(b) - hotScore(a) },
  newest: { label: '最新创建', fn: (a, b) => createdTs(b) - createdTs(a) },
  favorites: { label: '收藏最多', fn: (a, b) => (b.stats?.favorites || 0) - (a.stats?.favorites || 0) || hotScore(b) - hotScore(a) },
  difficulty: { label: '难度递增', fn: (a, b) => (DIFF_ORDER[a.difficulty] ?? 2) - (DIFF_ORDER[b.difficulty] ?? 2) },
}
// AppSelect 的选项数据（与 SORTERS 保持同一 key 顺序）
const SORT_OPTIONS = Object.entries(SORTERS).map(([value, { label }]) => ({ value, label }))
const sortBy = ref('hot')
const sortedItems = computed(() => {
  const arr = [...filteredItems.value]
  arr.sort(SORTERS[sortBy.value].fn)
  return arr
})

// 分页：客户端分页，筛选/搜索/排序变化时回到第一页
const PAGE_SIZE = 9
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(sortedItems.value.length / PAGE_SIZE)))
const pagedItems = computed(() => sortedItems.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))
watch([filter, category, keyword, sortBy], () => { page.value = 1 })
watch(totalPages, (total) => { if (page.value > total) page.value = total }) // 删除场景后收缩页码

const debatePage = ref(1)
const debateTotalPages = computed(() => Math.max(1, Math.ceil(filteredDebateTopics.value.length / PAGE_SIZE)))
const pagedDebateTopics = computed(() => filteredDebateTopics.value.slice((debatePage.value - 1) * PAGE_SIZE, debatePage.value * PAGE_SIZE))
watch([debateSourceFilter, keyword], () => { debatePage.value = 1 })
watch(debateTotalPages, (total) => { if (debatePage.value > total) debatePage.value = total })
const emptyTitle = computed(() => {
  if (keyword.value || category.value !== 'all') return '没有符合条件的内容'
  if (filter.value === 'favorited') return '还没有收藏的场景'
  if (filter.value === 'mine') return '还没有自己的场景'
  return '没有符合条件的内容'
})
const emptyDesc = computed(() => {
  if (keyword.value || category.value !== 'all') {
    return '换个关键词或分类试试，也可以清空筛选查看全部场景。'
  }
  if (filter.value === 'favorited') {
    return '在场景卡上点击收藏图标，常用的场景就会汇集在这里，方便快速开始训练。'
  }
  return '从内置模板复制一份，或从零创建属于你的训练场景；创建后默认仅本地可见，随时可发布。'
})

const canEdit = (scene) => scene.source !== 'builtin' && isMine(scene)
const sourceLabel = (scene) => {
  if (scene.source === 'builtin') return '内置'
  return scene.status === 'published' ? '已发布' : '本地'
}

// 作者头像：首字母 + 按名字哈希取底色（无用户系统头像字段时的轻量方案）
const AVATAR_COLORS = ['#6265e8', '#3d6bc4', '#3e7d5c', '#b8814a', '#b8485a', '#7059b8']
const avatarColor = (name) => {
  const sum = (name || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return AVATAR_COLORS[sum % AVATAR_COLORS.length]
}
const isOfficialAuthor = (scene) => scene?.source === 'builtin' || !scene?.author_name
const authorUser = (scene) => ({ id: scene.author_id, username: scene.author_name, avatar_path: scene.author_avatar_path })
const avatarInitial = (name) => (name || 'E').charAt(0).toUpperCase()
const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

// 难度五级（后端英文枚举存储，前端映射中文标签与配色）
const DIFFICULTIES = {
  entry: { label: '入门', cls: 'entry' },
  easy: { label: '简单', cls: 'easy' },
  normal: { label: '普通', cls: 'normal' },
  hard: { label: '困难', cls: 'hard' },
  expert: { label: '专家', cls: 'expert' },
}
const diffInfo = (value) => DIFFICULTIES[value] || DIFFICULTIES.normal
const diffLabel = (value) => diffInfo(value).label
const diffClass = (value) => diffInfo(value).cls

// 页面级加载：首屏场景列表返回前保持全局遮罩，删除/发布后的重新拉取只走页内骨架
const finishLoading = usePageLoading()
async function load() {
  initializing.value = true
  try {
    const [scenesRes, debateRes] = await Promise.allSettled([listScenes(), listDebateTopics()])
    if (scenesRes.status === 'fulfilled') {
      items.value = scenesRes.value.data.items
    } else {
      notify(scenesRes.reason?.message || '加载对话场景失败')
    }
    if (debateRes.status === 'fulfilled' && Array.isArray(debateRes.value.data?.items)) {
      debateTopics.value = debateRes.value.data.items
    }
  } finally {
    initializing.value = false
    finishLoading()
  }
}
onMounted(load)

// 卡片菜单：点击外部关闭
function toggleMenu(scene) {
  menuFor.value = menuFor.value === scene.id ? null : scene.id
}
function onGlobalClick() {
  menuFor.value = null
  debateMenuFor.value = null
}
function onEscKey(event) {
  if (event.key === 'Escape') {
    detail.value = null
    debateDetail.value = null
    deleteTarget.value = null
    conflict.value = null
  }
}
onMounted(() => {
  document.addEventListener('click', onGlobalClick)
  document.addEventListener('keydown', onEscKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onGlobalClick)
  document.removeEventListener('keydown', onEscKey)
})

// 详情弹窗：先用卡片摘要渲染，完整包异步并入同一对象（保持与卡片的引用同步）
async function openDetail(scene) {
  menuFor.value = null
  detail.value = scene
  try {
    const { data } = await getScene(scene.id)
    if (detail.value?.id === scene.id) Object.assign(detail.value, data)
  } catch (error) {
    notify(error.message)
  }
}

const activeTrainingScene = ref(null)
const trainingPhase = ref('select')

function startTraining(scene) {
  if (!scene?.id) return
  if (!session.token) return notify('开始训练需要先登录，点击左下角账户卡片登录。')
  if (!scene.stats?.favorited) {
    favRequiredHint.value = true
    return notify('请先收藏该场景，然后再开始训练。')
  }
  favRequiredHint.value = false
  detail.value = null
  trainingPhase.value = 'select'
  activeTrainingScene.value = scene
}

function goCreate() {
  if (!session.token) return notify('创建场景需要先登录，点击左下角账户卡片登录。')
  router.push({ name: 'scene-create' })
}
function goEdit(scene) {
  menuFor.value = null
  router.push({ name: 'scene-edit', params: { id: scene.id } })
}

// 导入：无冲突直接成功；冲突时弹窗让用户选覆盖或改名
function pickImport() {
  if (!session.token) return notify('导入场景需要先登录，导入后归入你的场景。')
  importInput.value.click()
}
const importInput = ref(null)
function handleImportFile(event) {
  const file = event.target.files?.[0]
  event.target.value = '' // 允许重复选择同一文件
  if (!file) return
  importScene(file)
    .then(({ data }) => {
      notify(data.action === 'renamed' ? `已改名导入为「${data.scene.name}」` : `导入成功：${data.scene.name}`)
      load()
    })
    .catch((error) => {
      if (error.code === 'SCENE_ID_CONFLICT') {
        conflict.value = { file, message: error.message }
      } else {
        notify(error.message)
      }
    })
}
function resolveImport(resolve) {
  const { file } = conflict.value
  conflict.value = null
  importScene(file, resolve)
    .then(({ data }) => {
      notify(data.action === 'overwritten' ? '已覆盖现有场景' : `已改名导入为「${data.scene.name}」`)
      load()
    })
    .catch((error) => notify(error.message))
}

async function doExport(scene) {
  menuFor.value = null
  try {
    await exportScene(scene.id)
    notify(`已导出「${scene.name}」`)
  } catch (error) {
    notify(error.message)
  }
}

async function doDuplicate(scene) {
  menuFor.value = null
  try {
    const { data } = await duplicateScene(scene.id)
    notify(`已复制为「${data.name}」，可自由编辑`)
    load()
  } catch (error) {
    notify(error.message)
  }
}

async function confirmDeleteTarget() {
  const target = deleteTarget.value
  if (!target) return
  if (target._isDebate) {
    deleteTarget.value = null
    await doDeleteDebate(target)
    return
  }
  await doDelete()
}

async function doDelete() {
  const scene = deleteTarget.value
  deleteTarget.value = null
  try {
    await deleteScene(scene.id)
    items.value = items.value.filter((item) => item.id !== scene.id)
    notify(`已删除「${scene.name}」`)
  } catch (error) {
    notify(error.message)
  }
}

async function doPublishToggle(scene) {
  menuFor.value = null
  try {
    if (scene.status === 'published') {
      await unpublishScene(scene.id)
      scene.status = 'private'
      notify('已取消发布，场景回到本地私有')
    } else {
      await publishScene(scene.id)
      scene.status = 'published'
      notify('已发布到社区，其他学习者可以查看与收藏')
    }
  } catch (error) {
    notify(error.message)
  }
}

// 点赞 / 收藏：游客引导登录；已登录乐观更新，失败回滚
async function toggleLike(scene) {
  if (!session.token) return notify('点赞需要先登录。')
  const liked = scene.stats?.liked
  scene.stats.likes = Math.max(0, (scene.stats.likes || 0) + (liked ? -1 : 1))
  scene.stats.liked = !liked
  try {
    const { data } = await likeScene(scene.id)
    scene.stats.likes = data.likes
    scene.stats.liked = data.liked
  } catch (error) {
    scene.stats.likes = Math.max(0, (scene.stats.likes || 0) + (liked ? 1 : -1))
    scene.stats.liked = liked
    notify(error.message)
  }
}
async function toggleFavorite(scene) {
  if (!session.token) return notify('收藏需要先登录。')
  const favorited = scene.stats?.favorited
  scene.stats.favorites = Math.max(0, (scene.stats.favorites || 0) + (favorited ? -1 : 1))
  scene.stats.favorited = !favorited
  try {
    const { data } = await favoriteScene(scene.id)
    scene.stats.favorites = data.favorites
    scene.stats.favorited = data.favorited
  } catch (error) {
    scene.stats.favorites = Math.max(0, (scene.stats.favorites || 0) + (favorited ? 1 : -1))
    scene.stats.favorited = favorited
    notify(error.message)
  }
}
</script>

<style scoped>
/* 场景探索页样式：沿用全局设计令牌，卡片扁平克制 */
.scenes-page { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 22px 28px 32px; overflow-y: auto; }

.scenes-toolbar { display: flex; flex: 0 0 auto; flex-wrap: wrap; row-gap: 8px; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 12px; }
.seg-filter { display: inline-flex; gap: 3px; padding: 3px; border: 1px solid var(--line); border-radius: 9px; background: var(--surface); }
.seg-item { display: inline-flex; align-items: center; gap: 6px; height: 31px; padding: 0 13px; border: 0; border-radius: 7px; background: transparent; color: var(--ink-soft); font-size: 13.5px; white-space: nowrap; transition: background .15s, color .15s; }
.seg-item:hover { color: var(--ink); }
.seg-item.active { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.seg-count { color: var(--muted); font-size: 11.5px; }
.seg-item.active .seg-count { color: var(--brand); }
.toolbar-actions { display: flex; align-items: center; gap: 9px; }
.hidden-input { display: none; }

/* 筛选行：分类 chips + 排序 + 搜索（排序下拉已提取为公共 AppSelect 组件） */
.filter-row { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 16px; }
.filter-right { display: flex; align-items: center; gap: 8px; }
.cat-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.cat-chip { height: 29px; padding: 0 13px; border: 1px solid var(--line); border-radius: 15px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, background .15s, color .15s; }
.cat-chip:hover { border-color: #d5d7e6; color: var(--ink); }
.cat-chip.active { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.search-box { position: relative; display: inline-flex; align-items: center; gap: 7px; width: 260px; height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--faint); transition: border-color .15s, box-shadow .15s; }
.search-box:focus-within { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(98, 101, 232, .12); }
.search-box input { flex: 1; min-width: 0; border: 0; outline: none; background: transparent; color: var(--ink); font-size: 13.5px; }
.search-box input::placeholder { color: var(--faint); }
.search-box input::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; display: none; } /* 隐藏原生清除按钮：避免与自绘清除按钮出现两个叉 */
.search-clear { display: grid; place-items: center; width: 18px; height: 18px; border: 0; border-radius: 50%; background: #eef0f5; color: var(--muted); transition: background .15s, color .15s; }
.search-clear:hover { background: #e3e5ee; color: var(--ink); }

.ghost-button { display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13.5px; transition: border-color .15s, color .15s, background .15s; }
.ghost-button:hover { border-color: #d5d7e6; color: var(--ink); background: #fafafd; }
.primary-button.slim { width: auto; height: 34px; margin-top: 0; gap: 6px; padding: 0 15px; justify-content: center; }
.danger-button { display: inline-flex; align-items: center; height: 34px; padding: 0 15px; border: 0; border-radius: 8px; background: var(--danger); color: #fff; font-size: 13.5px; font-weight: 500; transition: opacity .15s; }
.danger-button:hover { opacity: .9; }

.scene-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; align-content: start; flex: 1 0 auto; }
/* 卡片不裁切（overflow 可见），卡片菜单才能溢出卡片边界显示 */
.scene-card { display: flex; flex-direction: column; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); cursor: pointer; transition: border-color .18s, transform .18s, box-shadow .18s; animation: card-in .38s cubic-bezier(.22, .8, .32, 1) backwards; }
.scene-card:hover { border-color: #d8daea; transform: translateY(-2px); box-shadow: 0 6px 18px rgba(34, 37, 59, .06); }
@keyframes card-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.card-body { display: flex; flex-direction: column; flex: 1; padding: 14px 16px 16px; }

.card-head { display: flex; align-items: center; gap: 7px; margin-bottom: 11px; }
.mode-chip, .source-chip { display: inline-flex; align-items: center; gap: 4px; height: 22px; padding: 0 9px; border-radius: 6px; font-size: 11.5px; font-weight: 500; }
.mode-chip { background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.source-chip.builtin { background: #e3f2ea; color: #33684b; }
.source-chip.published { background: #e3ecfb; color: #33619f; }
.source-chip.private { background: #eeeff3; color: var(--ink-soft); }
.card-menu-anchor { position: relative; margin-left: auto; }
.menu-trigger { display: grid; width: 24px; height: 24px; place-items: center; border: 0; border-radius: 6px; background: transparent; color: var(--muted); transition: background .15s, color .15s; }
.menu-trigger:hover { background: #f0f1f6; color: var(--ink); }
.card-menu { position: absolute; top: calc(100% + 5px); right: 0; z-index: 12; min-width: 168px; padding: 5px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); box-shadow: 0 10px 28px rgba(34, 37, 59, .12); }
.menu-item { display: flex; width: 100%; height: 33px; align-items: center; gap: 8px; padding: 0 10px; border: 0; border-radius: 7px; background: transparent; color: var(--ink-soft); font-size: 13.5px; text-align: left; transition: background .12s, color .12s; }
.menu-item:hover { background: #f4f4f9; color: var(--ink); }
.menu-item.danger:hover { background: #fbf1f2; color: var(--danger); }
.menu-divider { height: 1px; margin: 4px 7px; background: var(--line); }

.card-title { margin: 0 0 6px; font-size: 15.5px; font-weight: 600; letter-spacing: -.01em; }
.card-desc { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; margin: 0; min-height: 40px; color: var(--muted); font-size: 13.5px; line-height: 1.55; text-wrap: pretty; }
.card-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
.tag-chip { padding: 3px 9px; border-radius: 5px; background: #edeff5; color: var(--ink-soft); font-size: 11.5px; }

/* 作者行 */
/* 作者行：margin-top:auto 与统计栏一起贴卡片底部，保证一排卡片底对齐 */
.card-author { display: flex; align-items: center; gap: 7px; margin-top: auto; padding-top: 12px; }
.avatar { display: grid; width: 22px; height: 22px; flex: 0 0 auto; place-items: center; border-radius: 50%; color: #fff; font-size: 11px; font-weight: 600; }
.avatar-logo { width: 22px; height: 22px; flex: 0 0 auto; border-radius: 50%; object-fit: cover; }
.author-name { color: var(--ink-soft); font-size: 12.5px; font-weight: 500; }
.author-date { margin-left: auto; color: var(--muted); font-size: 12px; }
.author-date { margin-left: 6px; }
/* 难度五级 chip：入门=绿 / 简单=青绿 / 普通=蓝 / 困难=橙 / 专家=红 */
.card-author .diff-chip { margin-left: auto; }
.diff-chip.entry { background: #e3f2ea; color: #2f7a52; }
.diff-chip.easy { background: #e0f2ef; color: #257a6b; }
.diff-chip.normal { background: #e3ecfb; color: #33619f; }
.diff-chip.hard { background: #fdefe0; color: #b26a24; }
.diff-chip.expert { background: #fbe7e7; color: #b03a3a; }

.card-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; padding-top: 11px; border-top: 1px solid var(--line); }
.card-meta { display: flex; flex-wrap: wrap; gap: 4px 10px; }
.meta-item { display: inline-flex; align-items: center; gap: 4px; color: var(--muted); font-size: 12px; }
.card-stats { display: inline-flex; align-items: center; gap: 3px; }
.stat-button { display: inline-flex; height: 25px; align-items: center; gap: 4px; padding: 0 7px; border: 0; border-radius: 6px; background: transparent; color: var(--muted); font-size: 12px; transition: background .15s, color .15s, transform .1s; }
.stat-button:hover { background: #f2f3f8; color: var(--ink); }
.stat-button:active { transform: scale(.92); }
.stat-button.on { color: var(--brand); }
.stat-button.on svg { fill: currentColor; }
/* 点赞=红 / 收藏=黄（激活态强化，详情统计图标常亮） */
.stat-button.on.like { color: #d6455d; }
.stat-button.on.fav { color: #d9930d; }
.detail-stats .stat-plain:nth-child(1) { color: #d6455d; }
.detail-stats .stat-plain:nth-child(2) { color: #d9930d; }
.stat-plain { display: inline-flex; align-items: center; gap: 4px; margin-left: 3px; color: var(--muted); font-size: 12px; }

.scenes-empty { grid-column: 1 / -1; display: grid; justify-items: center; padding: 46px 20px; border: 1px dashed var(--line); border-radius: 14px; background: rgba(255, 255, 255, .55); text-align: center; }
.empty-icon { display: grid; width: 48px; height: 48px; place-items: center; border: 1px solid #e3e4fb; border-radius: 12px; background: var(--brand-soft); color: var(--brand); }

/* 分页栏：随内容排在末尾（不做 sticky），靠 flex 撑到底部；矮窗口靠紧凑布局保证滚动到底即可见 */
.pagination { display: flex; flex-wrap: wrap; flex: 0 0 auto; justify-content: flex-end; align-items: center; gap: 6px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--line); }
.page-info { color: var(--muted); font-size: 12.5px; margin-right: 8px; }
.page-btn { display: inline-flex; align-items: center; gap: 4px; height: 31px; padding: 0 11px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-soft); font-size: 13px; transition: border-color .15s, color .15s, background .15s; }
.page-btn:hover:not(:disabled):not(.active) { border-color: #d5d7e6; color: var(--ink); }
.page-btn:disabled { opacity: .45; cursor: default; }
.page-num { width: 31px; justify-content: center; padding: 0; }
.page-num.active { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-deep, var(--brand)); font-weight: 500; }
.scenes-empty h3 { margin: 14px 0 6px; font-size: 16px; font-weight: 600; }
.scenes-empty p { margin: 0 0 16px; max-width: 400px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }

/* 骨架屏 */
.scene-card.skeleton { animation: none; cursor: default; }
.sk-line { height: 12px; margin-top: 10px; border-radius: 5px; background: linear-gradient(90deg, #eef0f5 25%, #f6f7fa 45%, #eef0f5 65%); background-size: 200% 100%; animation: shimmer 1.3s infinite; }
.sk-line.w40 { width: 40%; margin-top: 0; }
.sk-line.w80 { width: 80%; height: 14px; }
.sk-line.w60 { width: 60%; }
.sk-line.w70 { width: 70%; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }

/* 详情弹窗 */
.modal-backdrop { position: fixed; inset: 0; z-index: 40; display: grid; place-items: center; background: var(--scrim-bg, rgba(34, 37, 59, .28)); -webkit-backdrop-filter: var(--scrim-blur, blur(2px)); backdrop-filter: var(--scrim-blur, blur(2px)); animation: fade-in .18s ease; }
.modal-card { width: min(380px, calc(100vw - 48px)); padding: 24px; border-radius: 14px; background: var(--surface); box-shadow: 0 18px 48px rgba(34, 37, 59, .18); animation: pop-in .22s cubic-bezier(.22, .8, .32, 1); }
.modal-icon { display: grid; width: 38px; height: 38px; margin-bottom: 14px; place-items: center; border-radius: 10px; background: var(--brand-soft); color: var(--brand-deep, var(--brand)); }
.modal-icon.danger { background: #fbf1f2; color: var(--danger); }
.modal-card h3 { margin: 0 0 8px; font-size: 16.5px; font-weight: 600; }
.modal-card p { margin: 0 0 20px; color: var(--muted); font-size: 13.5px; line-height: 1.65; text-wrap: pretty; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }

.detail-card { position: relative; display: flex; flex-direction: column; width: min(620px, calc(100vw - 48px)); max-height: min(720px, calc(100vh - 96px)); overflow: hidden; border-radius: 16px; background: var(--surface); box-shadow: 0 24px 64px rgba(34, 37, 59, .2); animation: pop-in .22s cubic-bezier(.22, .8, .32, 1); }
.detail-close { position: absolute; top: 12px; right: 12px; z-index: 2; display: grid; width: 28px; height: 28px; place-items: center; border: 0; border-radius: 50%; background: rgba(34, 37, 59, .5); color: #fff; transition: background .15s; }
.detail-close:hover { background: rgba(34, 37, 59, .7); }
.detail-cover { flex: 0 0 auto; aspect-ratio: 21 / 9; overflow: hidden; }
.detail-cover img { display: block; width: 100%; height: 100%; object-fit: cover; }
.detail-content { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 20px 24px; overflow-y: auto; }
.detail-head h3 { margin: 0 0 10px; font-size: 20px; font-weight: 600; letter-spacing: -.01em; }
.detail-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.diff-chip, .cat-chip-static { display: inline-flex; align-items: center; height: 22px; padding: 0 9px; border-radius: 6px; background: #f1f2f7; color: var(--ink-soft); font-size: 11.5px; font-weight: 500; }
.detail-head .card-author { margin-top: 0; }
.detail-desc { margin: 14px 0 0; color: var(--ink-soft); font-size: 14px; line-height: 1.7; text-wrap: pretty; }
.detail-content .card-tags { margin-top: 12px; }
.detail-section { margin-top: 18px; }
.detail-section h4 { margin: 0 0 9px; color: var(--ink); font-size: 13.5px; font-weight: 600; }
.role-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px; }
.role-item { display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 9px; background: #fbfbfd; }
.role-name { color: var(--ink); font-size: 13.5px; font-weight: 600; }
.role-title { color: var(--muted); font-size: 12px; }
.objective-list { margin: 0; padding: 0; list-style: none; }
.objective-list li { display: flex; align-items: center; gap: 7px; padding: 6px 0; color: var(--ink-soft); font-size: 13.5px; }
.objective-list li svg { color: var(--brand); }
.doc-brief { margin: 0; padding: 0; list-style: none; }
.doc-brief li { display: flex; align-items: center; gap: 7px; padding: 5px 0; color: var(--ink-soft); font-size: 13.5px; }
.doc-chunks { margin-left: auto; color: var(--muted); font-size: 12px; }
.detail-fav-hint { display: flex; align-items: center; gap: 7px; padding: 9px 24px; border-top: 1px solid #f2e2b8; background: #fff9eb; color: #9a5b13; font-size: 13px; font-weight: 500; }
/* 底部操作栏：位于滚动容器外，固定贴底；自带左右 padding 与分隔线 */
.detail-foot { flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 24px 16px; border-top: 1px solid var(--line); background: var(--surface); border-radius: 0 0 16px 16px; }
.detail-stats { display: inline-flex; gap: 14px; }
.detail-actions { display: inline-flex; gap: 7px; }

.toast { position: fixed; top: 58px; left: 50%; z-index: 50; max-width: min(460px, calc(100vw - 40px)); padding: 9px 16px; border-radius: 9px; background: #2b2d4e; color: #fff; font-size: 13.5px; box-shadow: 0 10px 28px rgba(34, 37, 59, .22); animation: toast-in .22s cubic-bezier(.22, .8, .32, 1); }
.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
@keyframes fade-in { from { opacity: 0; } }
@keyframes pop-in { from { opacity: 0; transform: translateY(8px) scale(.97); } }
@keyframes toast-in { from { opacity: 0; transform: translate(-50%, -6px); } }
.toast-enter-active, .toast-leave-active { transition: opacity .2s, transform .2s; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, -6px); }
.toast { transform: translate(-50%, 0); }

@media (max-width: 860px) {
  .filter-row { flex-direction: column; align-items: stretch; }
  .filter-right { flex-wrap: wrap; }
  .search-box { width: 100%; }
  .detail-foot { flex-direction: column; align-items: stretch; }
  .detail-actions { justify-content: flex-end; }
}
/* 场景探索：筛选与卡片延续今日训练的轻卡通层次，内容仍以真实场景为主。 */
.scenes-page { padding: 24px clamp(18px, 2.4vw, 34px) 14px; background: #faf9ff; }
.scenes-toolbar { margin-bottom: 16px; }
.seg-filter { gap: 4px; padding: 4px; border: 1.5px solid #e9e5f1; border-radius: 13px; background: #fff; }
.seg-item { height: 34px; border-radius: 10px; font-weight: 600; }
.seg-item.active { background: #eee8ff; color: #694fc1; }
.cat-chip { min-height: 32px; border: 1.5px solid #ebe7f5; border-bottom-width: 3px; border-radius: 12px; font-weight: 600; }
.cat-chip.active { border-color: #a58ee9; border-bottom-color: #8067d1; background: #f0eaff; color: #654ab8; }
.scene-card { border: 1.5px solid #ebe7f5; border-bottom: 4px solid #e5def1; border-radius: 18px; background: #fff; }
.scene-card:hover { border-color: #cfc1f1; border-bottom-color: #d9cdef; box-shadow: 0 8px 18px #51408412; }
.card-body { padding: 16px 18px 17px; }
.card-title { color: #393451; font-weight: 750; }
.mode-chip, .source-chip, .tag-chip, .diff-chip { border-radius: 999px; }
.card-foot { border-color: #efedf5; }
.scenes-empty { border: 2px dashed #d9d0ef; border-radius: 18px; background: #fff; }
.empty-icon { width: 54px; height: 54px; border: 0; border-radius: 18px; background: #f0eaff; color: #8067d1; }
.primary-button.slim, .ghost-button, .danger-button { min-height: 38px; border-radius: 12px; font-weight: 650; }
.ghost-button { border: 1.5px solid #e9e5f1; border-bottom-width: 3px; }
.primary-button.slim { border: 1.5px solid #8067d1; border-bottom: 4px solid #6951b8; background: #8b73dd; }
.scene-card { overflow: visible; border-radius: 19px; }
/* 卡片 hover 时封面角标浮出（角标已收敛到 SceneCover 组件，需穿透作用域） */
.scene-card:hover :deep(.scene-cover-mark), .scene-card:focus-visible :deep(.scene-cover-mark) { opacity: 1; transform: translate(0, 0); }
.card-body { padding: 13px 17px 15px; }
.card-head { margin-bottom: 9px; }
.card-desc { min-height: 42px; }
.card-tags { margin-top: 8px; }
.tag-chip { padding: 4px 10px; background: #f2eff8; color: #655e78; }
.card-author { padding-top: 11px; }
.card-foot { margin-top: 10px; padding-top: 9px; }
/* 矮窗口（900×640 最小窗口）：收紧页头留白，优先保证首屏看到完整卡片与底部分页 */
@media (max-height: 700px) {
  .scenes-page { padding-top: 14px; }
  .scenes-toolbar { margin-bottom: 10px; }
  .filter-row { margin-bottom: 10px; }
  .scene-grid { gap: 12px; }
  .seg-item { height: 31px; }
  .cat-chip { min-height: 29px; }
}
/* 窄内容区（900×640 最小窗口内容区约 600px）：分段按钮与操作按钮不折行，筛选行整体换行排布 */
@media (max-width: 1080px) {
  .seg-item { padding: 0 9px; font-size: 12.5px; }
  .ghost-button, .primary-button.slim { white-space: nowrap; }
  .filter-row { flex-wrap: wrap; row-gap: 8px; }
  .cat-chips { flex: 1 1 100%; }
  .filter-right { flex: 1 1 100%; justify-content: flex-end; }
  .search-box { flex: 1 1 auto; max-width: 320px; }
}
.toolbar-left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.explore-mode-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border-radius: 14px;
  background: #f4f1fb;
  border: 1px solid #e6e0f3;
}

.explore-mode-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1.5px solid transparent;
  background: transparent;
  color: #655e78;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.explore-mode-tab.active {
  background: #ffffff;
  color: #5b44b6;
  border-color: #dcd3f2;
  border-bottom: 2px solid #c9bce8;
}

.mode-count {
  padding: 1px 7px;
  border-radius: 999px;
  background: #efeafc;
  color: #6e58c9;
  font-size: 11.5px;
  font-weight: 700;
}

.debate-motion-en {
  font-style: italic;
  color: #6b6480;
}

.debate-stance-mini {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8f6fc;
  border: 1px solid #ece7f6;
}

.stance-line {
  display: flex;
  gap: 8px;
  font-size: 12px;
  line-height: 1.45;
  color: #524b69;
}

.stance-line strong {
  flex-shrink: 0;
  color: #6e58c9;
}

.debate-enter-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #6e58c9;
  font-size: 12.5px;
  font-weight: 700;
}

.ghost-button.fav-active {
  border-color: #e4c158;
  background: #fff9e8;
  color: #9a6c08;
}

@media (prefers-reduced-motion: reduce) { .scene-card { transition: none; animation: none; } }
</style>
