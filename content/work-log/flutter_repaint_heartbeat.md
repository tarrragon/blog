---
title: "Flutter 畫面落後邏輯狀態（log 正確、畫面不符）— 重繪訊號排查與心跳兜底"
date: 2026-07-06
draft: false
description: "Flutter 畫面落後邏輯狀態（log 正確、畫面不符），含 platform view / 外部 texture 的渲染訊號沒進 frame 排程時回來讀。"
tags: ["flutter", "rendering", "platform-view"]
---

## 現象

畫面上的內容明明該更新了，實際卻**閃一下**、**跳過**某個狀態、或**凍在舊畫面**。但程式的 log 完全正確：狀態、計時、順序都對。

也就是**「log 正確、畫面不符」**——邏輯狀態是對的，實體畫面卻沒跟上。

## 原因

Flutter 是**按需重繪**：有內容要求時才排下一個 frame 去 build → paint → 合成 → 呈現（排 frame 的底層原語是 `scheduleFrame()`，設計意義見 [scheduleFrame()：按需 render 的最底層原語](../flutter_schedule_frame/)）。會要求排 frame 的來源有好幾種——widget 被標記 dirty（`setState`、動畫、依賴變更）、animation ticker 的每個 vsync、以及**外部 `Texture` 產生新影格時引擎自動排 frame**（Android 端 `SurfaceTexture` 的 frame-available 會通知引擎 `scheduleFrame`）。所以正常情況下，影片 / texture 這類平台端內容更新，是會驅動重繪的。

畫面落後邏輯狀態，發生在「該更新」這個訊號**沒有傳到 Flutter 的 frame 排程**。實際根因通常是這兩類，而不是「平台內容一律不驅動重繪」：

- **plugin / platform view 沒正確回報**：某個 plugin 更新了自己的畫面，卻沒呼叫 `markTextureFrameAvailable`；或 hybrid-composition platform view（原生 view 直接進 Flutter 合成樹的那種嵌入模式）的邊界情況，讓引擎不知道要排 frame。
- **邏輯改了值、卻沒觸發 rebuild**：你更新了 controller 或某個狀態，但顯示它的 widget 沒 `setState`、也沒監聽那個 controller，畫面就停在舊值。

這時實體畫面會停在最後一次重繪那一格，落後於邏輯狀態，表現成閃、跳、凍住。

> 一路在業務邏輯層修（計時、狀態切換時機）往往只是把同一個症狀換個樣子。**當 log 正確、畫面卻不符，就該懷疑重繪／合成這一層**——但第一步是查「更新訊號有沒有到 Flutter」（plugin 有沒有回報影格、你有沒有監聽 controller），而不是直接加心跳。

## 解法：先試正規解，心跳是兜底

多數情況下畫面落後是「訊號沒接上」，補一個監聽或請求排 frame 就好，不必疊心跳：

- **controller-backed widget（video_player 等）**：這類 plugin 的 controller 是 `ValueNotifier`，用 `addListener` 或 `ValueListenableBuilder` 監聽，狀態變就 rebuild。這是內容落後最正規的解。（這裡落後的是 controller 暴露的狀態值——播放位置、播放旗標等，跟 texture 影格是兩條路。）
- **真的要持續每幀刷新**：用 `Ticker` / `AnimationController(vsync:)`，每個 vsync 排一個 frame，是「每幀刷新」的慣用機制；偶爾推一個 frame 用 `WidgetsBinding.instance.scheduleFrame()`。
- **`RepaintBoundary`** 隔離重繪範圍，避免無關區域一起重畫。

### 兜底：定時強制排 frame

當 platform 端不配合、又改不動那個 plugin 時，最後手段是**定時強制排 frame**，讓合成層每隔一段時間重新 present 一次——composite 會把 texture 圖層的最新內容一起呈現。真正驅動的是「定時 `setState`／`scheduleFrame`」，跟畫面上顯示什麼無關（實測中一個可見的文字計數器、跟一個隱形的換色元件，效果一樣）。最小形式連 widget 都不用：

```dart
Timer.periodic(const Duration(milliseconds: 200), (_) {
  WidgetsBinding.instance.scheduleFrame();
});
```

如果偏好包成一個可以疊進畫面的隱形 widget，下面是一個版本：

```dart
/// 重繪心跳：讓 Flutter 持續排 frame、畫面即時刷新。
/// 每 200ms 重繪一次角落 1px、每次換一個肉眼看不出的顏色（內容必須有變才會觸發呈現）。
/// 1px、近乎全透明，不留可見痕跡。
class FramePump extends StatefulWidget {
  const FramePump({super.key});

  @override
  State<FramePump> createState() => _FramePumpState();
}

class _FramePumpState extends State<FramePump> {
  int _tick = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(milliseconds: 200), (_) {
      if (mounted) setState(() => _tick++);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Align(
        alignment: Alignment.topLeft,
        child: SizedBox(
          width: 1,
          height: 1,
          child: CustomPaint(painter: _FramePumpPainter(_tick)),
        ),
      ),
    );
  }
}

class _FramePumpPainter extends CustomPainter {
  const _FramePumpPainter(this.tick);

  final int tick;

  @override
  void paint(Canvas canvas, Size size) {
    // 在兩個近乎全透明、肉眼看不出的顏色間交替；內容有變才會觸發重新呈現
    final paint = Paint()
      ..color = tick.isEven ? const Color(0x01000000) : const Color(0x01010000);
    canvas.drawRect(const Rect.fromLTWH(0, 0, 1, 1), paint);
  }

  @override
  bool shouldRepaint(_FramePumpPainter oldDelegate) => oldDelegate.tick != tick;
}
```

疊進畫面（放在 Stack 最上層即可）：

```dart
Stack(
  fit: StackFit.expand,
  children: [
    yourContentLayer,
    const FramePump(), // 重繪心跳
  ],
)
```

### 更精簡：scheduleFrame 版包成 widget

不需要 `CustomPaint` 換色那套——用 timer 定時 `scheduleFrame`、widget 本身什麼都不畫，同時把 timer 的生命週期收在 `initState`／`dispose`：

```dart
class FramePump extends StatefulWidget {
  const FramePump({super.key});

  @override
  State<FramePump> createState() => _FramePumpState();
}

class _FramePumpState extends State<FramePump> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(milliseconds: 200), (_) {
      WidgetsBinding.instance.scheduleFrame();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
```

不 `setState`、不重繪任何 widget，只是每 200ms 請引擎排一個 frame；比 `setState + CustomPaint` 版少了 rebuild 與 paint 的開銷，是實務上比較推薦的隱形 widget 形式。

## 幾個關鍵細節

- **驅動的是 tick、不是顏色**：`setState(() => _tick++)` 讓 widget dirty、排一個 frame，`shouldRepaint` 比對 tick（每次必變）觸發 paint。上面兩個 `const` 顏色交替其實可省——`shouldRepaint` 根本沒看顏色，而且 present 出去的是整張重新合成的 frame，引擎不會因為某層像素相同就跳過呈現。要更精簡就用前面的 `scheduleFrame` 版、連 CustomPaint 都不需要。
- **要隱形**：1px、alpha 只有 `0x01`（近乎全透明），肉眼看不出。
- **頻率**：200ms（約 5fps）通常就夠讓內容變化即時呈現，不必 60fps 狂刷。
- **`IgnorePointer`**：避免這層攔截觸控。
- **背景不排 frame**：`scheduleFrame` 受 `framesEnabled` 約束，app 進背景時不會排——前景播放的情境沒問題，若真要不論可見性都推 frame 才需 `scheduleForcedFrame()`。

## 判斷是否是這個問題

- **log 顯示邏輯正確**（狀態、計時、順序都對），但實體畫面落後、閃、跳、凍住。
- 內容以**靜態為主**，或含 **platform view / 外部 texture**（影片播放器等），而畫面更新的訊號沒反映到 Flutter 的 frame 排程。

符合以上，先查「更新訊號有沒有到 Flutter」——plugin 有沒有正確回報 texture 影格、你有沒有監聽 controller。確認 platform 端不配合、又改不動時，才用定時強制排 frame 兜底，而不是繼續在業務邏輯層打轉。
