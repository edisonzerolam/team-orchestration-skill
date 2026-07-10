#!/usr/bin/env python3
"""检测中文乱码（mojibake）文件。扫描 .md 文件，检测是否包含乱码特征。"""
import os, re
from pathlib import Path

SKILL_DIR = Path(r"C:\Users\林昌\.config\opencode\skills\team-orchestration")
# 常见乱码特征字符（通过分析 UTF-8 double-transcode 产生的异常 CJK 字符）
MOJIBAKE_CHARS = set(
    '鍥㈤槦鑴戝崗浼佷笟娉曞姟鍩烘湰淇℃伅鍚嶇О鏁伴噺瑙﹀彂璇存槑宸ョ▼淇濋殰璁捐寮曟搸'
    '鏁版嵁鍒嗘瀽鍐呭鍒涗綔鍙樼幇鍟嗕笟妯″紡鏀剁泭浼樺寲椤鹃棶鏋舵瀯娉曞緥鍜ㄨ鍚堝悓瀹℃煡'
    '鍔冲姩娉曞氬Щ娉曢棶棰樺浗闄呯瓥鐣ュ崌绾х‖浠跺姞閫熷崱鐗囧紑鍙戞墜鍐屽弬鑰冩枃妗ｆ'
    '绱㈤〉闈㈠姛鑳芥帴鍙ｅ畨鍏ㄦ父鎴忕敤鎴锋帴鍙ｅ疄鐜拌嚜鍔ㄥ寲绯荤粺宸ュ叿鏁版嵁搴撴湇鍔″櫒'
    '绠＄悊鎺т欢缁勪欢妯″潡鎺ュ彛绉佹湁鍗忚闆嗘垚娴嬭瘯閮ㄧ讲鍙戝竷鐩戞帶鏃ュ織'
    '閸欐牠顦崣鏍閺嬪倸鐗忛梻浣稿簻濞嗘劙顢旈崼婵堝灮濞ｇ偓绶ラ柨婵嗗闁靛海鐓熼柡鍥敆'
    '閸ャ垽妲﹂崥宥囆�鏉≌冿拷鐟欙箑褰傜拠鐠佹崘顓稿��鏇熸惛閸愬懎顔愰崚娑楃稊閺佺増宓侀崚鍡樼�介崶銏ゆЕ'
    '濞夋洖绶ラ崪銊�顕楅崶銏ゆЕ閸愬懎顔愰崚鍡楀絺閸愬懎顔愰崣妯煎箛鐠佹崘顓稿��鏇熸惛瀹搞儳鈻兼穱婵嬫�?'
)

def count_mojibake_chars(text: str) -> int:
    """统计文本中 mojibake 特征字符的数量"""
    return sum(1 for c in text if c in MOJIBAKE_CHARS)

def main():
    md_files = list(SKILL_DIR.rglob("*.md"))
    mojibake_files = []
    for path in md_files:
        # 跳过 __pycache__ 和 .git
        rel = path.relative_to(SKILL_DIR)
        if any(p.startswith('.') or p == '__pycache__' for p in path.parts):
            continue
        try:
            text = path.read_bytes().decode('utf-8')
        except:
            try:
                text = path.read_bytes().decode('gbk')
            except:
                print(f"  [!] {rel}: 完全无法解码")
                continue
        count = count_mojibake_chars(text)
        if count > 5:
            mojibake_files.append((rel, count))

    if mojibake_files:
        print(f"[FAIL] 发现 {len(mojibake_files)} 个文件存在中文乱码:")
        for rel, count in sorted(mojibake_files, key=lambda x: -x[1]):
            print(f"  ❌ {rel} (mojibake chars: {count})")
        print()
        print("提示: 这些文件的中文内容已损坏，无法通过重新编码修复。")
        print("恢复方法：从 Git 历史 checkout、从备份恢复、或重新生成。")
        return 1
    else:
        print("[OK] 未检测到中文乱码文件")
        return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
