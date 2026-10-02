# musicdl-gui 修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 musicdl_gui 代码审查中发现的功能错误、Flet API 兼容性问题、竞态条件和代码质量问题。

**Architecture:** 按优先级分阶段修复：先修复功能错误，再修复竞态条件，最后清理代码质量。每个修复独立可测试。

**Tech Stack:** Python 3.10+, Flet 1.0+, flet-audio, asyncio

**Spec:** 基于 2026-10-02 代码审查报告

## Global Constraints

- 不改变现有 API 签名（除非修复 bug 需要）
- 保持 Flet 1.0 兼容性
- 每个修复后运行 `pytest` 确保不引入回归
- 每个修复后运行 `ruff check src/musicdl_gui/` 确保代码风格

---

## Phase 1: 立即修复（功能错误）

### Task 1: 修复 PlaybackBar 方法名冲突

**Files:**
- Modify: `src/musicdl_gui/playback/bar.py:150-188`

**问题:** 两个同名方法 `_on_progress_change` 导致 Slider 拖动失效。第二个定义（182行）覆盖了第一个（150行），而 Slider 的 `on_change` 需要第一个签名。

**修复:**
- [ ] 将第 150 行的 `_on_progress_change` 重命名为 `_on_slider_change`
- [ ] 更新第 47 行 `on_change=self._on_progress_change` 为 `on_change=self._on_slider_change`
- [ ] 保留第 182 行的 `_on_progress_change`（用于 service 回调）

---

### Task 2: 删除 service.py 死代码

**Files:**
- Modify: `src/musicdl_gui/playback/service.py:294-296`

**问题:** `return` 语句后有永远不会执行的 `import flet_audio as fta` 和注释。

**修复:**
- [ ] 删除第 294-296 行的死代码

---

### Task 3: 修复播放索引越界检查

**Files:**
- Modify: `src/musicdl_gui/playback/service.py:238-244`

**问题:** `% len(self._playlist)` 保证索引 < len，导致 `>=` 检查永远不成立。顺序播放到最后一首后会循环而非停止。

**修复:**
- [ ] 移除取模运算，改为 `self._current_index += 1`
- [ ] 保留 `>= len(self._playlist)` 检查来触发 ENDED 状态
- [ ] 同样修复第 259 行的相同模式

---

### Task 4: 修复暂停后无法恢复播放

**Files:**
- Modify: `src/musicdl_gui/playback/service.py:113-128,199-268`

**问题:** `pause()` 设置 `_state = PAUSED` 导致 `_playback_loop` 退出。再次 `play()` 创建新 loop 但 `_audio` 已被 release，无法从暂停位置恢复。

**修复:**
- [ ] 在 `play()` 方法中检测从 PAUSED 恢复的情况
- [ ] 如果 `_audio` 存在且未 release，调用 `self._audio.resume()` 而非重新下载
- [ ] 如果 `_audio` 为 None（被 stop 了），则重新开始播放
- [ ] 修改 `_playback_loop` 使其在暂停时等待而非退出

---

### Task 5: 重构播放队列管理逻辑

**Files:**
- Modify: `src/musicdl_gui/playback/service.py:92-111,158-184,199-268`

**问题:** 当前使用索引管理播放列表，逻辑复杂且存在多个 bug（索引越界、不自动切歌、暂停无法恢复）。

**新方案:** 使用队列（FIFO）管理播放列表，始终播放第一首，播放完成后弹出。

**修复:**
- [ ] 修改 `set_playlist()`：将歌曲列表存入 `_playlist` 队列
- [ ] 修改 `play()`：始终播放 `_playlist[0]`（第一首）
- [ ] 修改 `_playback_loop()`：
  - 播放完成后，若模式为 SINGLE_LOOP，不弹出，继续播放第一首
  - 若模式为 RANDOM，使用 `random.shuffle()` 重新打乱 `_playlist`
  - 其他模式：弹出第一首（`pop(0)`）
  - 若弹出后 `_playlist` 为空，设置 `_state = ENDED` 并退出
- [ ] 修改 `next_track()`：弹出第一首，播放新的第一首
- [ ] 修改 `previous_track()`：需要维护历史记录或使用不同策略
- [ ] 移除 `_current_index` 相关逻辑，改用队列操作
- [ ] 确保 `_current_item` 始终指向 `_playlist[0]`

**注意:** 此重构会影响 Task 3（索引越界）和 Task 4（暂停恢复），建议先执行 Task 5，然后重新评估 Task 3/4 是否仍需修复。

---

### Task 6: 修复 FilePicker API 调用

**Files:**
- Modify: `src/musicdl_gui/tabs/error_log.py:59-64`

**问题:** `file_picker.save_file_async()` 不存在。官方文档确认：正确方法是 `save_file()`，且 FilePicker 需加到 `page.services`。

**修复:**
- [ ] 将 `file_picker.save_file_async()` 改为 `await file_picker.save_file()`
- [ ] 将 `self.page.services.append(file_picker)` 改为正确添加到 `page.services`
- [ ] 桌面模式下 `save_file()` 返回选中的文件路径，无需 `src_bytes`

---

### Task 7: 修复 AlertDialog 的 open 属性

**Files:**
- Modify: `src/musicdl_gui/playback/dialog.py:215-221`

**问题:** `AlertDialog` 无 `open` 属性，应使用 `page.show_dialog()` / `page.pop_dialog()`。

**修复:**
- [ ] 修改 `_close()` 调用 `self._page.pop_dialog()`
- [ ] 修改 `show()` 调用 `self._page.show_dialog(self)`
- [ ] 移除 `self.open = False/True` 赋值

---

## Phase 2: 高优先级（竞态条件）

### Task 8: 修复 stop() 竞态条件

**Files:**
- Modify: `src/musicdl_gui/playback/service.py:140-156`

**问题:** `stop()` 同步置 `_audio = None`，但 `_playback_loop` 可能正在访问 `_audio`。

**修复:**
- [ ] 在 `_playback_loop` 中每次访问 `_audio` 前检查是否为 None
- [ ] 或使用 `try/except AttributeError` 包裹音频操作
- [ ] 在 `stop()` 中先设置状态，再异步 release

---

### Task 9: 修复 seek() 竞态条件

**Files:**
- Modify: `src/musicdl_gui/playback/service.py:186-193`

**问题:** `seek()` 同步更新 `_progress`，与 `_on_position_change` 回调冲突。

**修复:**
- [ ] 添加 `_seeking` 标志防止 seek 期间的位置更新
- [ ] 或在 `_on_position_change` 中检查是否正在 seek

---

### Task 10: 修复 error_log.py 线程安全

**Files:**
- Modify: `src/musicdl_gui/error_log.py:104-110`

**问题:** `_entries` 的 append + slice 非原子；callback 异常会中断后续 callback。

**修复:**
- [ ] 添加 `threading.Lock` 保护 `_entries` 和 `_callbacks`
- [ ] 用 `try/except` 包裹每个 callback 调用
- [ ] 确保锁范围最小化

---

### Task 11: 修复未 await 的协程调用

**Files:**
- Modify: `src/musicdl_gui/tabs/playlist_browser.py:116`

**问题:** `self._show_snack(...)` 是 async 函数但未 await。

**修复:**
- [ ] 将 `_on_track_download` 改为 async 方法
- [ ] 添加 `await` 调用
- [ ] 更新调用处 `on_download=self._on_track_download` 的绑定

---

## Phase 3: 中优先级（代码质量）

### Task 12: 删除重复定义的 _show_snack

**Files:**
- Modify: `src/musicdl_gui/tabs/playlist_browser.py:124-127`

**问题:** `_show_snack` 方法在第 51 行和第 124 行重复定义。

**修复:**
- [ ] 删除第 124-127 行的重复定义

---

### Task 13: 删除重复定义的变量

**Files:**
- Modify: `src/musicdl_gui/playback/dialog.py:88-89`

**问题:** `current_time` 和 `duration_text` 在第 36-37 行和第 88-89 行重复定义。

**修复:**
- [ ] 删除第 88-89 行的重复定义

---

### Task 14: 修复 callable 类型注解

**Files:**
- Modify: `src/musicdl_gui/components/track_list.py:12-13`

**问题:** `callable` 是内置函数不是类型，应为 `Callable`。

**修复:**
- [ ] 添加 `from collections.abc import Callable`
- [ ] 将 `on_download: callable` 改为 `on_download: Callable`
- [ ] 将 `on_play: callable` 改为 `on_play: Callable`

---

### Task 15: 修复 subprocess import 位置

**Files:**
- Modify: `src/musicdl_gui/playback/service.py:272,288`

**问题:** `import subprocess` 在 try 内部，except 中引用可能失败。

**修复:**
- [ ] 将 `import subprocess` 移到文件顶部
- [ ] 或改为 `except Exception` 避免引用未绑定变量

---

### Task 16: 修复 api.py 类型注解

**Files:**
- Modify: `src/musicdl_gui/api.py:41,46`

**问题:** `func` 类型应为 `Callable[[], Awaitable[T]]` 而非 `Callable[[], T]`。

**修复:**
- [ ] 修改 `_with_retry` 的 `func` 参数类型
- [ ] 添加 `from collections.abc import Awaitable` 或使用 `typing.Awaitable`

---

## Phase 4: 验证

### Task 17: 运行测试验证

**Files:**
- Test: `tests/`

**步骤:**
- [ ] 运行 `pytest` 确保所有测试通过
- [ ] 运行 `ruff check src/musicdl_gui/` 确保代码风格
- [ ] 运行 `pyright src/musicdl_gui/` 确认类型错误已修复
- [ ] 手动测试播放、暂停、切歌功能
- [ ] 测试 FilePicker 导出功能
- [ ] 测试 AlertDialog 全屏播放功能

---

## 执行建议

### Subagent Review 机制（强制执行）

每个 Task 完成后，必须按以下流程进行：

1. **执行 Subagent** 完成 Task 实现
2. **Review Subagent** 独立审查代码变更
   - 检查是否完全解决原问题
   - 检查是否引入新 bug 或回归
   - 运行 `pytest` `ruff` `pyright` 验证
   - 如发现问题，输出具体问题清单
3. **如 Review 发现问题**：
   - 派发 **Fix Subagent** 修复 Review 指出的问题
   - 修复完成后，**再次派发新的 Review Subagent** 复查
   - 循环直到 Review 通过（无问题）
4. **Review 通过后**：提交 commit，进入下一个 Task

**关键规则：**
- 执行 Subagent 和 Review Subagent 必须是不同的 agent 实例
- 每次 Review 失败必须派发新的 Fix Subagent，不允许原执行者自行修复
- 只有 Review 明确通过才能 commit

---

### 常规执行建议

1. 按 Phase 顺序执行，每个 Phase 完成后运行测试
2. 每个 Task 完成后提交 commit
3. 如果某个修复引入新问题，回滚该 Task 并重新设计
4. Phase 4 验证通过后，考虑更新 AGENTS.md 中过时的 Flet API 说明
