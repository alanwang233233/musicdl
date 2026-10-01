#!/usr/bin/env python3
"""下载歌单 2249180720 全部音乐到 /Volumes/数据 #3/music"""

import time
import urllib.parse
import requests
from pathlib import Path
from musicdl import (
    MusicDLConfig,
    SyncMusicClient,
    PlaylistService,
    SongService,
    DownloadService,
)
from musicdl.exceptions import APIError, NetworkError, DownloadError

PLAYLIST_ID = "2249180720"
OUTPUT_DIR = Path("/Volumes/数据 #3/music")
QUALITY = "hires"
MAX_RETRIES = 10
RATE_LIMIT_WAIT = 10  # 限流等待秒数

def sanitize_filename(name: str) -> str:
    return name.replace("/", ";")

def download_with_retry(downloader, song_service, track, quality, output_path, max_retries=MAX_RETRIES):
    """带重试的下载，遇到 429/404 自动等待重试"""
    for attempt in range(max_retries + 1):
        try:
            # 先获取 URL 以确定真实扩展名
            url_info = song_service.get_url(track.id, level=quality)
            if not url_info.url:
                raise APIError(code=404, message="Song URL is null/unavailable")
            import urllib.parse
            parsed = urllib.parse.urlparse(url_info.url)
            ext = Path(parsed.path).suffix or ".mp3"
            target_path = output_path.with_suffix(ext)
            
            if target_path.exists():
                return target_path, "skipped"
            
            path = downloader.download_song(
                track.id,
                level=quality,
                output=target_path,
            )
            return path, "success"
            
        except (APIError, NetworkError, DownloadError, requests.HTTPError) as e:
            # 解包 DownloadError 获取原始异常
            original = e
            if isinstance(e, DownloadError) and e.__cause__:
                original = e.__cause__
            
            # 检查是否为限流错误 (429) 或 404
            is_rate_limit = False
            is_not_found = False
            if isinstance(original, APIError):
                if original.code == 429:
                    is_rate_limit = True
                if original.code == 404:
                    is_not_found = True
                if hasattr(original, 'payload') and isinstance(original.payload, dict):
                    if original.payload.get('code') == 429:
                        is_rate_limit = True
            elif isinstance(original, requests.HTTPError):
                # MP3 下载返回 404/429
                if original.response is not None:
                    status = original.response.status_code
                    if status == 429:
                        is_rate_limit = True
                    elif status == 404:
                        is_not_found = True
            
            # NetworkError (客户端重试耗尽) 也视为可重试
            is_network_error = isinstance(original, NetworkError)
            
            if is_rate_limit or is_not_found or is_network_error:
                if attempt < max_retries:
                    wait_time = RATE_LIMIT_WAIT
                    if is_rate_limit:
                        error_type = "限流(429)"
                    elif is_not_found:
                        error_type = "未找到(404)"
                    else:
                        error_type = "网络错误"
                    print(f"  ⏳ {error_type}，等待 {wait_time}s 后重试 ({attempt+1}/{max_retries})...", end="\r")
                    time.sleep(wait_time)
                    continue
            # 非限流错误或重试耗尽，抛出
            raise
    # 重试耗尽
    raise Exception(f"重试 {max_retries} 次后仍失败")

def main():
    config = MusicDLConfig()
    
    with SyncMusicClient(config) as client:
        playlist_service = PlaylistService(client)
        song_service = SongService(client)
        downloader = DownloadService(
            song_service,
            playlist_service,
            output_dir=OUTPUT_DIR,
            naming_template="{singer} - {title}",
            progress_callback=lambda done, total: (
                print(f"  进度: {done}/{total} bytes" if total > 0 else f"  进度: {done} bytes", end="\r")
            ),
        )
        
        print(f"正在获取歌单 {PLAYLIST_ID} 信息...")
        playlist = playlist_service.get_all_tracks(PLAYLIST_ID)
        
        print(f"\n=== 歌单信息 ===")
        print(f"名称: {playlist.name}")
        print(f"ID: {playlist.id}")
        print(f"歌曲数: {playlist.song_count}")
        print(f"播放量: {playlist.play_count}")
        print(f"标签: {', '.join(playlist.tags) if playlist.tags else '无'}")
        print(f"创建者: {playlist.creator.name} (UID: {playlist.creator.uid})")
        print(f"简介: {playlist.description or '无'}")
        print(f"封面: {playlist.cover_image}")
        
        print(f"\n=== 曲目列表 (共 {len(playlist.songs)} 首) ===")
        for i, track in enumerate(playlist.songs, 1):
            print(f"  {i:3d}. {track.name} - {track.singer}")
            print(f"       专辑: {track.album} | 时长: {track.duration} | 免费: {'是' if track.free else '否'} | 版权: {track.copyright.name}")
        
        print(f"\n开始下载到: {OUTPUT_DIR}")
        print("-" * 50)
        
        paths = []
        failed = []
        skipped = []
        for i, track in enumerate(playlist.songs, 1):
            # 清理文件名中的 / \ 
            safe_singer = sanitize_filename(track.singer)
            safe_name = sanitize_filename(track.name)
            
            base_path = OUTPUT_DIR / f"{safe_singer} - {safe_name}"
            
            # 检查是否已存在（任意扩展名）
            existing = list(OUTPUT_DIR.glob(f"{safe_singer} - {safe_name}.*"))
            if existing:
                print(f"\n[{i}/{len(playlist.songs)}] {track.singer} - {track.name}")
                print(f"  ⊘ 已存在，跳过: {existing[0].name}")
                skipped.append(existing[0])
                continue
            
            print(f"\n[{i}/{len(playlist.songs)}] {track.singer} - {track.name}")
            try:
                path, status = download_with_retry(downloader, song_service, track, QUALITY, base_path)
                if status == "skipped":
                    skipped.append(path)
                    print(f"  ⊘ 已存在，跳过: {path.name}")
                else:
                    paths.append(path)
                    print(f"  ✓ 已下载: {path.name}")
            except Exception as e:
                failed.append((track, e))
                import traceback
                print(f"  ✗ 失败: {e}")
                if e.__cause__:
                    print(f"     原因: {e.__cause__}")
                elif e.__context__:
                    print(f"     上下文: {e.__context__}")
                else:
                    traceback.print_exc()
        
        print(f"\n{'='*50}")
        print(f"完成！成功下载 {len(paths)} 首，跳过 {len(skipped)} 首，失败 {len(failed)} 首")
        for p in paths:
            print(f"  ✓ {p.name}")
        if skipped:
            print(f"\n跳过列表:")
            for p in skipped:
                print(f"  ⊘ {p.name}")
        if failed:
            print(f"\n失败列表:")
            for track, err in failed:
                print(f"  ✗ {track.singer} - {track.name}: {err}")

if __name__ == "__main__":
    main()