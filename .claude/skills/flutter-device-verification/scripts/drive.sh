#!/bin/bash
# 操作執行中的 Flutter APP 並截圖。
#
# 環境變數：
#   FLUTTER_APP_DIR   APP 專案根目錄（讀它的 .dart_tool/package_config.json，drive.dart 要用其中的 vm_service）
#   FLUTTER_VM_WS     VM service 的 WebSocket 位址，例如 ws://127.0.0.1:54376/Fl0QQR6W8sg=/ws
#   ANDROID_SERIAL    Android 設備序號（截 Android 時設）
#   IOS_UDID          iOS 模擬器 UDID（截 iOS 時設）；兩者擇一，兩個都設時截 Android
#   WAIT              每個動作之後等的秒數，預設 0.8（Flutter 3.41 預設換頁：Material 450ms、Cupertino 500ms）
#   SHOT              有設時，動作成功之後截圖存到這個路徑（會覆寫同名檔）；動作失敗時不截
#   SHOT_LOG          有設時，每張截圖成功後在這個檔附加一行：日期與時間、截圖路徑、APP 的 commit、
#                     工作樹狀態（clean，或未提交改動與未追蹤檔內容的雜湊前 8 碼；APP 不在 git 底下時是 no-git）
#   SHOT_DELAY        截圖前等的秒數，預設 1.2（等喚醒之後的畫面亮起）；輪詢短暫出現的畫面時設 0
#
# 用法：
#   drive.sh push <route> [arg] | tap <x> <y> | longpress <x> <y> | drag <x1> <y1> <x2> <y2> | back | type <text> | dpr
#   drive.sh eval <運算式>  在 APP 的函式庫求值並印出結果（不等 WAIT；只留輸出的最後一行）
#   drive.sh shot <path>    只截圖，不操作（面板或對話框開著時用這個，不要點畫面角落觸發）
#   drive.sh wake           送喚醒鍵（Android；腳本操作不算系統觸控，不會延長螢幕逾時）
#
# eval 以外的動作之後等 0.8 秒讓換頁動畫跑完（Flutter 3.41 預設 Material 450ms、Cupertino 500ms），longpress 從放開算起
# 同樣等 0.8 秒；動作送得太密時，實測（Android 16 實機、iPhone 16 模擬器，Flutter 3.41）之後的操作不再換頁。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ADB="${ADB:-$(command -v adb || echo "${ANDROID_HOME:-$HOME/Library/Android/sdk}/platform-tools/adb")}"

screenshot() {
  local out="${1:?截圖路徑}"
  if [ -n "${ANDROID_SERIAL:-}" ]; then
    "$ADB" -s "$ANDROID_SERIAL" shell input keyevent KEYCODE_WAKEUP
    sleep "${SHOT_DELAY:-1.2}"
    # 先寫暫存檔，成功才換成正式檔名：失敗時不把同名的舊圖蓋成空檔
    "$ADB" -s "$ANDROID_SERIAL" exec-out screencap -p > "$out.tmp" || { rm -f "$out.tmp"; return 1; }
    [ -s "$out.tmp" ] || { rm -f "$out.tmp"; echo "drive.sh: 截圖是空的" >&2; return 1; }
    mv "$out.tmp" "$out"
  elif [ -n "${IOS_UDID:-}" ]; then
    sleep "${SHOT_DELAY:-1.2}"
    xcrun simctl io "$IOS_UDID" screenshot "$out" >/dev/null || return $?
  else
    echo "drive.sh: 沒有設 ANDROID_SERIAL 或 IOS_UDID，無法截圖" >&2
    return 2
  fi
  log_shot "$out"
}

log_shot() {
  [ -n "${SHOT_LOG:-}" ] || return 0
  local rev tree hasher
  hasher=$(command -v shasum || command -v sha1sum) || {
    echo "drive.sh: 找不到 shasum 或 sha1sum，SHOT_LOG 沒有寫入" >&2
    return 1
  }
  local st
  if ! rev=$(git -C "${FLUTTER_APP_DIR:?}" rev-parse --short HEAD 2>/dev/null); then
    # 不在 git 底下時讀不到版本：記成 no-git，不記成 clean，免得每張圖看起來都是同一版
    echo "drive.sh: $FLUTTER_APP_DIR 不在 git 底下，SHOT_LOG 記成 no-git，截圖分不出版本" >&2
    rev="-"
    tree=no-git
  elif st=$(git -C "$FLUTTER_APP_DIR" status --porcelain 2>/dev/null) && [ -z "$st" ]; then
    tree=clean
  else
    # 未提交的改動、未追蹤的檔名與它們的內容一起算雜湊：只有新檔時 diff 是空的，
    # 只算檔名的話，改了新檔的內容雜湊也不變
    tree="dirty:$({ git -C "$FLUTTER_APP_DIR" diff HEAD 2>/dev/null; printf '%s\n' "$st"; (cd "$FLUTTER_APP_DIR" && git ls-files -o --exclude-standard -z | xargs -0 -r cat 2>/dev/null); } | "$hasher" | cut -c1-8)"
  fi
  printf '%s\t%s\t%s\t%s\n' "$(date '+%F %T')" "$1" "$rev" "$tree" >> "$SHOT_LOG"
}

case "${1:-}" in
  shot)
    screenshot "${2:?截圖路徑}"
    exit $?
    ;;
  wake)
    "$ADB" -s "${ANDROID_SERIAL:?wake 只用在 Android}" shell input keyevent KEYCODE_WAKEUP
    exit $?
    ;;
  "")
    echo "用法：drive.sh <push|tap|longpress|drag|back|type|dpr|eval|shot|wake> ..." >&2
    exit 2
    ;;
esac

[ -n "${ANDROID_SERIAL:-}" ] && "$ADB" -s "$ANDROID_SERIAL" shell input keyevent KEYCODE_WAKEUP
dart --packages="${FLUTTER_APP_DIR:?}/.dart_tool/package_config.json" "$HERE/drive.dart" "${FLUTTER_VM_WS:?}" "$@" | tail -1
status=${PIPESTATUS[0]}
WAIT="${WAIT:-0.8}"   # APP 自訂的換頁動畫比 0.8 秒長時，設 WAIT 拉長
case "${1:-}" in
  eval) ;;                                 # 只讀狀態或呼叫函式，不換頁；輪詢時不能每次多等
  longpress) sleep 0.7; sleep "$WAIT" ;;   # 放開在 700ms 之後
  drag) sleep 0.35; sleep "$WAIT" ;;       # 拖曳約 300ms
  *) sleep "$WAIT" ;;
esac
if [ -n "${SHOT:-}" ]; then
  if [ "$status" -eq 0 ]; then
    screenshot "$SHOT" || status=$?
  else
    echo "drive.sh: 動作失敗（exit ${status}），沒有截圖" >&2
  fi
fi
exit "$status"
