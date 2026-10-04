"""Pure-logic tests for PlaybackService (no flet page / audio involved)."""

from musicdl_gui.models import QueueItem
from musicdl_gui.playback.service import PlaybackMode, PlaybackService, PlaybackState
from musicdl_gui.playback.temp_manager import TempFileManager


class _StubPage:
    """Records run_task calls without scheduling anything."""

    def __init__(self):
        self.tasks = []

    def run_task(self, coro_fn, *args):
        self.tasks.append((coro_fn, args))


def _item(song_id: int, title: str) -> QueueItem:
    return QueueItem(
        song_id=song_id,
        title=title,
        singer="Singer",
        playlist="",
        quality="standard",
        output_path=None,
    )


def _service() -> tuple[PlaybackService, _StubPage]:
    page = _StubPage()
    service = PlaybackService(
        queue=None,
        config_manager=None,
        temp_manager=TempFileManager(),
        page=page,
    )
    return service, page


class _WithDuration:
    def __init__(self, seconds: float):
        self._seconds = seconds

    def total_seconds(self):
        return self._seconds


class _WithTotalMilliseconds:
    def total_milliseconds(self):
        return 2500


class _WithInMillisecondsProperty:
    @property
    def in_milliseconds(self):
        return 3000


class _WithMillisecondsAttr:
    milliseconds = 4000


def test_to_seconds_variants():
    service, _ = _service()
    assert service._to_seconds(_WithDuration(1.5)) == 1.5
    assert service._to_seconds(_WithTotalMilliseconds()) == 2.5
    assert service._to_seconds(_WithInMillisecondsProperty()) == 3.0
    assert service._to_seconds(_WithMillisecondsAttr()) == 4.0
    assert service._to_seconds(5000) == 5.0
    assert service._to_seconds(object()) == 0.0


def test_set_playlist_sets_current():
    service, _ = _service()
    service.set_playlist([_item(1, "A"), _item(2, "B")])
    assert service.current_item.title == "A"
    assert len(service._playlist) == 2


def test_next_track_moves_current_to_history():
    service, page = _service()
    service.set_playlist([_item(1, "A"), _item(2, "B"), _item(3, "C")])
    service.next_track()
    assert service.current_item.title == "B"
    assert [i.title for i in service._history] == ["A"]
    # 任务重启与当前状态无关(BUFFERING 期间切歌此前会静默丢歌)
    assert len(page.tasks) == 1


def test_previous_track_does_not_duplicate_current():
    service, _ = _service()
    service.set_playlist([_item(1, "A"), _item(2, "B")])
    service.next_track()  # current=B, history=[A], playlist=[B, C]... 检查下方
    service._playlist = [service._current_item] if service._current_item else []
    service.previous_track()
    titles = [i.title for i in service._playlist]
    # current 不应在列表中出现两次
    assert titles.count(service._current_item.title) == 1


class _StubAudio:
    def pause(self):
        return None

    def release(self):
        return None

    def seek(self, milliseconds):
        return None


def test_stop_resets_seeking_and_state():
    service, _ = _service()
    service.set_playlist([_item(1, "A")])
    service._seeking = True
    service._audio = _StubAudio()
    service.stop()
    assert service._seeking is False
    assert service.state == PlaybackState.STOPPED
    assert service.current_item is None
    assert service._audio is None


def test_add_to_playlist_while_playing_appends_without_interrupting():
    """播放中追加整单(Play All 语义):只入队,不发 track_change,不启动新任务。"""
    service, page = _service()
    service.set_playlist([_item(1, "A")])
    fired: list = []
    service.add_on_track_change(fired.append)
    service._state = PlaybackState.PLAYING

    service.add_to_playlist(_item(2, "B"))
    service.add_to_playlist(_item(3, "C"))

    assert [i.title for i in service._playlist] == ["A", "B", "C"]
    assert fired == []
    assert page.tasks == []


def test_add_to_playlist_on_empty_playlist_sets_current():
    """空闲时追加:第一个入队项成为当前曲目并通知 UI。"""
    service, _page = _service()
    fired: list = []
    service.add_on_track_change(fired.append)

    service.add_to_playlist(_item(2, "B"))
    service.add_to_playlist(_item(3, "C"))

    assert service.current_item.title == "B"
    assert [i.title for i in service._playlist] == ["B", "C"]
    assert len(fired) == 1


def test_add_to_playlist_next_inserts_after_current():
    """播放中"下一首播放":插入到当前曲目之后,不打断播放、不发 track_change。"""
    service, page = _service()
    service.set_playlist([_item(1, "A"), _item(2, "B")])
    fired: list = []
    service.add_on_track_change(fired.append)
    service._state = PlaybackState.PLAYING

    service.add_to_playlist_next(_item(3, "C"))

    assert [i.title for i in service._playlist] == ["A", "C", "B"]
    assert service.current_item.title == "A"
    assert fired == []
    assert page.tasks == []


def test_add_to_playlist_next_on_empty_sets_current():
    """空闲时"下一首播放":等同直接入队并成为当前曲目。"""
    service, _page = _service()

    service.add_to_playlist_next(_item(1, "A"))

    assert service.current_item.title == "A"
    assert [i.title for i in service._playlist] == ["A"]


def test_position_event_beyond_duration_is_clamped():
    """音频尾部上报的位置可能略超已知时长,progress 必须钳制到 0..1,
    否则 Slider.value 超过 max 触发 flet 校验错误。"""
    service, _ = _service()
    fired: list = []
    service.add_on_progress_change(lambda p, d: fired.append((p, d)))
    service._audio = _StubAudio()
    service._duration = 100.0

    service._on_position_change(service._audio, 100500)  # 100.5s > 100s
    assert fired[-1] == (1.0, 100.0)

    service._last_progress_emit = 0.0  # 重置节流窗口
    service._on_position_change(service._audio, -50)  # 异常负值同样钳制
    assert fired[-1] == (0.0, 100.0)

    service._last_progress_emit = 0.0
    service._on_position_change(service._audio, 30000)  # 正常值不受影响
    assert fired[-1] == (0.3, 100.0)


def test_completed_audio_marks_track_finished_not_ended():
    """曲目自然播完只打完成标记,不得置 ENDED——
    否则播放循环在每首歌播完后退出,单曲循环/自动连播失效。"""
    import flet_audio as fta

    service, _ = _service()
    service.set_playlist([_item(1, "A")])
    service._audio = _StubAudio()
    service._track_completed = False

    service._on_flet_audio_state_change(service._audio, fta.AudioState.COMPLETED)

    assert service._track_completed is True
    assert service.state != PlaybackState.ENDED


def test_duration_event_overrides_estimate():
    """播放器上报的真实时长必须覆盖 ffprobe/估算值——
    高码率下 128kbps 估算偏长数倍,进度条会提前卡在某个比例。"""
    service, _ = _service()
    service._audio = _StubAudio()
    service._duration = 240.0  # 估算值(偏大)

    service._on_duration_change(service._audio, _WithDuration(100.0))
    assert service._duration == 100.0

    service._on_duration_change(service._audio, _WithDuration(0.0))  # 无效值忽略
    assert service._duration == 100.0


def test_seek_suppression_times_out():
    """seek 后 1 秒内抑制进度回写;若完成事件丢失,超时后必须自动恢复更新。"""
    service, _ = _service()
    service._audio = _StubAudio()
    service._duration = 100.0
    fired: list = []
    service.add_on_progress_change(lambda p, d: fired.append(p))

    service.seek(0.5)
    assert fired[-1] == 0.5  # seek 自身同步回显

    service._on_position_change(service._audio, 10000)  # 1 秒内:抑制
    assert len(fired) == 1

    service._seek_requested_at -= 2.0  # 人为让 seek 超时
    service._on_position_change(service._audio, 20000)
    assert fired[-1] == 0.2
    assert service._seeking is False


async def test_single_loop_downloads_once_and_replays(tmp_path, monkeypatch):
    """单曲循环:同一首歌只下载一次,播完立即用同一临时文件重播。"""
    service, _page = _service()
    service.set_playlist([_item(1, "A")])
    service.mode = PlaybackMode.SINGLE_LOOP
    service._state = PlaybackState.PLAYING  # play() 在启动任务前置的状态

    downloads: list[int] = []

    async def fake_acquire(item):
        downloads.append(item.song_id)
        p = tmp_path / "single.mp3"
        p.write_bytes(b"x")
        return p

    async def fake_duration(path):
        return 30.0

    plays: list = []

    async def fake_play(path):
        plays.append(path)
        if len(plays) >= 2:
            service._generation += 1  # 模拟外部接管,结束循环

    monkeypatch.setattr(service, "_acquire_temp", fake_acquire)
    monkeypatch.setattr(service, "_get_audio_duration", fake_duration)
    monkeypatch.setattr(service, "_play_audio_file", fake_play)

    await service._playback_loop(service._generation)

    assert downloads == [1]  # 只下载一次
    assert len(plays) == 2  # 重播一次
    assert plays[0] == plays[1]  # 复用同一临时文件
    assert service._single_loop_temp == plays[0]  # 文件保留供同曲重播复用


async def test_sequential_auto_advances_to_ended(tmp_path, monkeypatch):
    """顺序模式:播完自动切下一首,列表耗尽后进入 ENDED。"""
    service, _page = _service()
    service.set_playlist([_item(1, "A"), _item(2, "B")])
    service._state = PlaybackState.PLAYING

    async def fake_acquire(item):
        return tmp_path / f"{item.song_id}.mp3"

    async def fake_duration(path):
        return 10.0

    plays: list = []

    async def fake_play(path):
        plays.append(path)

    monkeypatch.setattr(service, "_acquire_temp", fake_acquire)
    monkeypatch.setattr(service, "_get_audio_duration", fake_duration)
    monkeypatch.setattr(service, "_play_audio_file", fake_play)

    await service._playback_loop(service._generation)

    assert len(plays) == 2
    assert service.state == PlaybackState.ENDED
    assert service.current_item is None


async def test_prefetch_starts_near_track_end(tmp_path, monkeypatch):
    """剩余不足 20 秒且存在下一首时触发预取;完成前不重复;单曲循环不预取。"""
    service, _page = _service()
    service.set_playlist([_item(1, "A"), _item(2, "B")])
    service._state = PlaybackState.PLAYING
    service._audio = _StubAudio()
    service._duration = 100.0

    downloaded: list[int] = []

    async def fake_download(item):
        downloaded.append(item.song_id)
        p = tmp_path / f"prefetch_{item.song_id}.mp3"
        p.write_bytes(b"x")
        return p

    monkeypatch.setattr(service, "_download_to_temp", fake_download)

    # 剩余 30 秒:不预取
    service._progress = 0.7
    service._maybe_start_prefetch()
    assert service._prefetch_tasks == {}

    # 剩余 10 秒:预取下一首
    service._progress = 0.9
    service._maybe_start_prefetch()
    assert 2 in service._prefetch_tasks
    path = await service._prefetch_tasks[2]
    assert downloaded == [2]
    assert service._prefetched_paths[2] == path

    # 预取完成后不重复下载
    service._maybe_start_prefetch()
    assert downloaded == [2]

    # 单曲循环模式不预取
    service.mode = PlaybackMode.SINGLE_LOOP
    service._prefetched_paths.clear()
    service._maybe_start_prefetch()
    assert 2 not in service._prefetch_tasks
    assert downloaded == [2]


async def test_acquire_temp_prefers_prefetched_file(tmp_path):
    """正式播放时优先命中预取缓存,避免重复下载。"""
    service, _page = _service()
    cached = tmp_path / "cached.mp3"
    cached.write_bytes(b"x")
    service._prefetched_paths[7] = cached

    got = await service._acquire_temp(_item(7, "Cached"))

    assert got == cached
    assert 7 not in service._prefetched_paths
