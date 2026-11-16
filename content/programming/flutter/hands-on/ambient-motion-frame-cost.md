---
title: "Flutter 裝飾性動畫的驅動方式比較：AnimationController、Ticker、Timer 與事件觸發的 frame 數與 CPU 量測"
date: 2026-11-16
description: "在 Flutter 裡做一個會隨風擺動的裝飾元件，想知道 AnimationController、Ticker、Timer 與事件觸發各自讓渲染管線一秒跑幾次時讀：可重做的量測 app 與完整程式碼、FrameTiming 與 paint 次數的取法、144 Hz 螢幕上的實測結果與讀法。"
weight: 1
tags: ["flutter", "animation", "rendering", "performance", "hands-on"]
---

2026-11-16 在一台 macOS 15（Darwin 24.3）的 Mac 上做的量測：Flutter 3.41.3（Dart 3.11.1），以 profile 模式跑 macOS 桌面版，app 視窗開在一台更新率 144 Hz 的外接螢幕上。當時在驗證一個預期：把像素遊戲裡「樹被風吹動」的做法搬進 App 時，姿勢一秒只換 10 次能不能讓渲染管線也一秒只跑 10 次。同一天換了兩個場景各量一輪，每一輪用同一份程式跑兩次自動量測：簡化樹那一輪用一棵 48 × 56 格、14 叢葉子的樹，畫面 288 × 336 邏輯點，每一幀逐格畫方塊；橡樹與松樹那一輪把場景換成造型接近原文截圖的一棵橡樹與一棵松樹，畫面放大到 672 × 400 邏輯點，繪製改成重播啟動時錄好的 `Picture`。兩輪的驅動方式、運動模型與計數的程式相同。下文的「輪」指場景，「次」指同一個場景重跑。每一輪的第二次，`flutter run` 印出 `Failed to foreground app; open returned 1`，app 視窗沒有被帶到最前面；兩次的幀數與每幀柵格化時間相近。

這篇是一次可以重做的量測：用程式畫出一棵拆成葉叢（clump：樹冠拆成一團一團、各自位移的葉子圖塊）的橡樹與一棵拆成枝層的松樹，讓五種驅動方式共用同一個運動模型，分別是不動（static）、`AnimationController` 每個 [vsync](/ux-design/knowledge-cards/vsync/) 都算（smooth）、`Ticker` 每個 vsync 醒而姿勢 100 ms 才換（tickerStepped）、`Timer` 每 100 ms 算一次（timerStepped）、事件來了才起 `Timer`（eventDriven）；app 用 `addPersistentFrameCallback`、`addTimingsCallback` 與 `CustomPainter.paint` 的計數量每一種方式一秒跑幾次 framework frame、raster frame 與繪製，另外每秒取樣一次行程的 CPU 使用率；接著是兩次實測的結果與量測前預測的對照、跟簡化樹那一輪的對照（兩輪之間場景的造型、畫面大小與繪製方式同時改變，各種驅動方式的每幀 build、柵格化時間與 CPU 取樣各自怎麼變），以及 tickerStepped 為什麼繪製次數降了、柵格化次數沒有降；完整的 `lib/main.dart` 附在文末。同一個場景改繪製方式、降低每一幀柵格化時間的做法與量測，寫在〔[Flutter 像素場景的每幀柵格化成本](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)〕。運動模型本身的設計（事件觸發、位置相位、中心穩邊緣鬆）與這個結果在 App 設計上的意義，寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕。

## 量測需要的環境：Flutter SDK、Mac 與螢幕更新率

- Flutter SDK，`flutter doctor` 的 macOS 那一項是綠的（要有 Xcode）。這次用 3.41.3，下文引用的 `Ticker.scheduleTick()` 與 `RendererBinding.drawFrame()` 是這一版的原始碼；換版本時，先在 SDK 的 `packages/flutter/lib/src/scheduler/ticker.dart` 與 `rendering/binding.dart` 確認這兩段還是同樣的寫法。數字會因機器而不同。
- 一台 Mac。量的是幀數，不需要實機手機；手機上的耗電要另外用 Xcode Instruments 的 Energy Log，或 Android Studio 的 Power Profiler（Hedgehog 以後的版本，需要支援 ODPM 的 Pixel 6 以後機型）量，這次沒有做。
- 知道自己的螢幕更新率：系統設定 → 顯示器 → 更新頻率。下文每個 vsync 都排幀的兩種方式（`AnimationController` 平滑動畫的 smooth、`Ticker` 每幀醒而姿勢低頻換的 tickerStepped），每秒的幀數會等於這個值，在 60 Hz 的螢幕上就是每秒 60 次左右。接了好幾台更新率不同的螢幕時，幀數跟著 app 視窗所在的那一台：這次的 Mac 接了一台 60 Hz 與一台 144 Hz 的螢幕，視窗開在 144 Hz 那一台；要拿來跟本篇的數字比，把視窗拖到要量的那一台（自動量測在 app 啟動 2 秒之後才開始，來得及拖），或先把那一台設成主螢幕。

## 建立量測用的 Flutter macOS 專案

```bash
flutter create --platforms=macos --project-name wind_sway_demo wind-sway-demo
```

`flutter create` 帶 `--platforms=macos` 時只產生 macOS 的 runner（包住 Flutter app 的原生殼專案），因為這次只在桌面上量；要在手機上跑時，在同一個專案裡再跑一次 `flutter create --platforms=ios,android .` 補上。`--project-name` 是 Dart package 名，只能用小寫字母、數字與底線；`wind_sway_demo` 是這次取的名稱，沒有比較其他值，後面 CPU 取樣的 `pgrep` 用這個名稱比對行程，換了名稱那一行要跟著改。最後一個引數 `wind-sway-demo` 是資料夾名，也是這次取的名稱，不影響後續步驟。

完整的 `lib/main.dart` 在文末〈附錄：完整的 `lib/main.dart`〉，整份取代 `flutter create` 產生的範例。範例附帶的 `test/widget_test.dart` 引用的 `MyApp` 在取代之後就不存在了，`flutter analyze` 會報 `The name 'MyApp' isn't a class`、`flutter test` 會失敗；這個測試跟量測無關，刪掉它，或改成引用 `DemoApp`。下面各段只列出跟量測結論有關的片段，`Tree.build()`、`samePose()`、`gustEnvelope()`、`TreePainter` 與自動量測的切換程式碼只放在附錄。之後的指令都在專案資料夾 `wind-sway-demo` 裡跑。

## 量測：framework frame、raster frame 與 paint 的計數器

渲染管線一次跑下來，可以在 framework、engine 與場景的繪製這幾處計數，各處的次數不一定相同：

```dart
class Stats {
  Stats._();
  static final Stats instance = Stats._();

  int frameworkFrames = 0; // drawFrame 被呼叫的次數
  int rasterFrames = 0; // engine 回報的 FrameTiming 數
  int paints = 0; // 場景的 CustomPainter.paint 次數
  int rasterMicros = 0;
  int buildMicros = 0;

  void install() {
    SchedulerBinding.instance.addPersistentFrameCallback((_) => frameworkFrames++);
    SchedulerBinding.instance.addTimingsCallback((timings) {
      rasterFrames += timings.length;
      for (final t in timings) {
        rasterMicros += t.rasterDuration.inMicroseconds;
        buildMicros += t.buildDuration.inMicroseconds;
      }
    });
  }
}

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  Stats.instance.install();
  runApp(const DemoApp());
}
```

- **framework frame**：`addPersistentFrameCallback` 註冊的回呼在每一次 `drawFrame` 都會被呼叫一次，所以它數的是 framework 端跑了幾次版面、繪製與合成。
- **raster frame**：`addTimingsCallback` 收到的每一筆 [`FrameTiming`](/programming/flutter/knowledge-cards/frame-timing/) 代表 engine 柵格化並送出了一幀。engine 會批次回報，`SchedulerBinding.addTimingsCallback` 的文件寫的間隔是 profile 與 debug 模式大約 100 ms 一批、release 模式大約 1 秒一批，所以這個數字只拿來算一段時間的總數，不拿來對齊單一幀。`rasterDuration` 與 `buildDuration` 累加起來，除以幀數就是平均每幀的柵格化與 build 時間。
- **paint**：在場景的 `CustomPainter.paint` 第一行把計數加一，數的是場景這一層真正重畫了幾次。

`WidgetsFlutterBinding.ensureInitialized()` 要在 `install()` 之前：`SchedulerBinding.instance` 在 binding 建立之前是 null，少了這一行，app 一啟動就在 `Stats.install` 拋出 `Null check operator used on a null value`。這次第一次啟動量測時就停在這個錯誤上。

`flutter run` 不帶模式旗標時是 debug 模式，服務的是開發中的 hot reload 與斷言檢查；這次要量的是接近出貨版本的幀數，所以改用 profile 模式。debug 模式的 Dart 程式碼跑在 JIT 上，還開著各種斷言，每一幀的時間比實際出貨的版本長，`FrameTiming` 的文件也註明 debug 模式的數字跟 profile、release 模式不同。profile 模式用 AOT 編譯、關掉斷言，同時保留 DevTools 連得上的 timeline；release 模式的 `FrameTiming` 一樣拿得到，但 DevTools 的 timeline 拿掉了，要對照 timeline 時就沒有材料。

## 場景與運動模型：橡樹、松樹與位移公式

場景由程式產生、不用圖檔：168 × 100 格，每格畫成 4 × 4 邏輯點的方塊，下文的「格」都指這個方塊，對應原文（SpriteCook〈[Pixel art trees in the wind](https://www.spritecook.ai/blog/pixel-art-trees-wind-animation)〉）的一個像素。場景裡並排一棵橡樹與一棵松樹，顏色、光影與拆法參考原文的截圖；所有隨機值都來自固定的種子與一個固定的整數雜湊，所以每次啟動產生的樹都一樣，五種驅動方式下 app 畫的是完全相同的內容。兩個尺寸與下面的各項參數都是這次取的值，沒有比較其他值。

- **橡樹**：樹冠由 32 叢葉子組成，七排由上往下排成扁寬的半球，上排先畫、下排後畫，下排疊在上排前面。每一叢是圓形加上三個不同頻率的正弦起伏，邊緣再加每格的雜訊；光從左上來，每叢左上亮、右下暗，右緣與下緣畫最暗的輪廓；色相依整棵樹的左右位置從黃綠漸變到藍綠。內層是整個樹冠往內縮兩格、顏色乘 0.45 的暗色版本，葉叢之間的縫與葉叢移開時露出來（原文是內縮 2 像素、顏色乘 0.55）。樹幹往下漸寬、底部撐開成根，在樹冠下方分岔成枝幹。
- **松樹**：9 層往下垂的枝層，越往下越寬；每一層上亮下暗，下緣是一束束垂下的針葉。下層先畫、上層後畫，上層的下緣蓋在下層上面，上面幾層之間露出樹幹。原文用 shader 把松樹幹逐列平移，做出彎曲；這裡樹幹不動，只讓枝層擺動。

每一叢（每一層）在啟動時錄成一張 [`ui.Picture`](/programming/flutter/knowledge-cards/picture/)，拆法上相當於原文「每一叢一張 sprite」（原文的 sprite 是已經畫好的點陣圖，`Picture` 則是繪圖指令，每一幀重播時 raster 執行緒仍要重新柵格化，兩者的成本差別與改用點陣圖的做法在〔[Flutter 像素場景的每幀柵格化成本](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)〕）；樹幹、內層與草錄成一張背景的 `Picture`。每一幀的繪製是重播一次背景的 `Picture`，再把 41 張葉叢與枝層的 `Picture` 各自依位移平移後重播，不重新計算每一格的顏色。這 41 張 `Picture` 都畫進同一個 `CustomPainter`，所以整個場景在圖層樹裡只有一個圖層。

每一叢帶一個權重：橡樹是 0.35 + 0.65 × (葉叢中心到樹冠中心的距離 ÷ 34 格)，上限 1.0，中心穩、邊緣鬆；34 格是這次取的正規化距離，大約是樹冠中心到外圈葉叢的距離，再外面的葉叢權重都是 1.0；松樹是 0.35 + 0.65 × 這一層的相對高度，越高的層擺得越多，用來模擬原文樹幹上段彎曲、枝層跟著移動的效果。原文只寫了橡樹的權重從中心的 0.35 線性增加到邊緣的 1.0。位移的公式取自原文：

```dart
List<Offset> computePose(Tree tree, double t, double breeze, double gust, double lean,
    {required bool quantize}) {
  return [
    for (final c in tree.clumps)
      () {
        final along = c.cx + 0.25 * c.cy; // 葉叢在風向上的位置
        final a = 2 * math.pi * (t / 1.54 - along / 69); // 位置決定相位
        final w = c.weight; // 中心小、邊緣大
        final dx = lean * w + w * (0.9 * breeze + 1.3 * gust) * (0.5 - 0.5 * math.cos(a));
        final dy = -w * (0.75 * breeze + 0.5 * gust) * math.max(math.sin(a), 0);
        return quantize ? Offset(dx.roundToDouble(), dy.roundToDouble()) : Offset(dx, dy);
      }(),
  ];
}
```

- `t` 是秒數；1.54 秒是一個擺動循環的長度，69 是兩個波峰之間隔幾格（原文寫 69 像素）。`along` 的 `0.25 * c.cy` 也取自原文：畫面的 y 往下增加，所以同一個水平位置上，低處的葉叢晚一點被吹到，波前是斜的。
- `gust` 是這一刻的陣風強度，0 到 1。`breeze` 在原文是陣風周圍那一圈較弱的風場，陣風走遠之後也落回 0，所以原文的樹在陣風之間是靜止的。這次為了量「一直在動」的成本，smooth、tickerStepped、timerStepped 三種方式把 `breeze` 固定在 0.8、`gust` 固定為 0；`breeze` 不落回 0 這一點跟原文不同。0.8 是這次取的值，沒有比較其他值。它決定擺幅，擺幅再決定取整之後的姿勢多常改變：擺幅大到每 100 ms 幾乎都有一叢跨過整數格時，姿勢每次都變，paint 接近每秒 10 次；擺幅調小時，取整之後不變的次數變多，paint 會低於 10，framework frame 與 raster frame 不受影響。eventDriven 用 `breeze = 0`、`gust` 由事件決定，比較接近原文。
- `lean` 是樹身彈簧的傾斜量，單位是格；`quantize` 為 true 時位移取整數格，也就是原文的整數像素跳格。

樹身的彈簧用原文橡樹的參數（推力 2.2、週期 2.2 秒、阻尼比 0.35）：

```dart
class Spring {
  double lean = 0;
  double speed = 0;
  static const double push = 2.2;
  static const double period = 2.2;
  static const double damping = 0.35;

  void step(double gust, double dt) {
    final k = 2 * math.pi / period;
    speed += (k * k * (push * gust - lean) - 2 * damping * k * speed) * dt;
    lean += speed * dt;
  }

  bool get settled => lean.abs() < 0.05 && speed.abs() < 0.05;
}
```

`settled` 的門檻 0.05 是這次取的值，沒有比較其他值；它比取整的門檻 0.5 小一個數量級，程式判定彈簧靜止時，取整之後的位移一定已經是 0。

`CustomPainter.shouldRepaint` 比較新舊兩組位移，完全相同就回 false：姿勢沒變時，framework 即使跑了一幀也不會重畫這一層。場景包在 [`RepaintBoundary`](/programming/flutter/knowledge-cards/repaint-boundary/) 裡，場景這一層重畫時不會連帶重畫畫面上的其他元件。

## 驅動方式：static、smooth、tickerStepped、timerStepped、eventDriven

這五種方式寫在同一個 `StatefulWidget`（`with TickerProviderStateMixin`）的 `initState` 裡，依模式選一種：

```dart
switch (widget.mode) {
  case Mode.static:
    break;
  case Mode.smooth:
    controller = AnimationController(vsync: this, duration: const Duration(seconds: 1))
      ..addListener(() => setState(() {
            pose = computePose(widget.tree, t, kBreeze, 0, 0, quantize: false);
          }))
      ..repeat();
  case Mode.tickerStepped:
    ticker = createTicker((elapsed) {
      if (elapsed - lastPoseAt < kPoseInterval) return; // 每個 vsync 都進來，大多直接返回
      lastPoseAt = elapsed;
      final next = computePose(widget.tree, t, kBreeze, 0, 0, quantize: true);
      if (!samePose(next, pose)) setState(() => pose = next);
    })
      ..start();
  case Mode.timerStepped:
    timer = Timer.periodic(kPoseInterval, (_) {
      final next = computePose(widget.tree, t, kBreeze, 0, 0, quantize: true);
      if (!samePose(next, pose)) setState(() => pose = next);
    });
  case Mode.eventDriven:
    if (kAuto) {
      autoEvents = Timer.periodic(const Duration(seconds: kEventEverySeconds), (_) => gust());
    }
}
```

- **smooth** 是一般寫動畫的預設做法：`AnimationController.repeat()` 讓 controller 底下的 `Ticker` 每個 vsync 觸發一次，每一次都 `setState`，位移不取整。它是對照組，代表「用平滑動畫做同一件事」的成本。
- **tickerStepped** 的驅動結構取自原文：原文的彈簧每一幀都更新、姿勢 10 Hz 才換，所以驅動器每個 vsync 都要觸發。搬進 Flutter 就是 `Ticker` 每個 vsync 觸發、回呼裡判斷距離上次換姿勢滿 100 ms 了沒，沒滿就直接返回，不呼叫 `setState`。這個模式省掉彈簧（`lean` 固定 0）：彈簧只改變每一叢的位移，`Ticker` 每個 vsync 都觸發這件事不看位移，所以彈簧有沒有算不改變排幀的次數，只增加回呼裡的計算量。
- **timerStepped** 的驅動器換成 `Timer.periodic`：一秒只觸發 10 次，每次算一次姿勢，有變才 `setState`。100 ms 取自原文的 `POSE_TIME := 0.1`；這次沒有比較其他間隔。間隔改短，姿勢換得更密、動作更平滑，渲染管線的次數照比例增加；改長，跳格更明顯，這個運動模型在 200 ms 以上看起來會變成一格一格的停頓（從原文的週期推論：1.54 秒的循環在 200 ms 間隔下只剩 7 到 8 個姿勢，這次沒有實跑）。
- **eventDriven** 平常不排任何一幀，事件發生時才起 `Timer`：

```dart
void gust() {
  if (widget.mode != Mode.eventDriven) return;
  eventAt = t;
  timer ??= Timer.periodic(kPoseInterval, (_) {
    final since = t - eventAt!;
    final g = gustEnvelope(since); // 事件後 2.4 秒內從 0 升到 1 再落回 0
    for (var i = 0; i < 6; i++) {
      spring.step(g, 1 / 60); // 彈簧用 1/60 秒的子步長積分
    }
    final next = computePose(widget.tree, t, 0, g, spring.lean, quantize: true);
    final rest = g == 0 && spring.settled && next.every((o) => o == Offset.zero);
    if (!samePose(next, pose)) setState(() => pose = next);
    if (rest) {
      timer?.cancel(); // 風停、樹回正：停掉驅動器
      timer = null;
    }
  });
}
```

程式在每一次 `Timer` 觸發時用 6 個 1/60 秒的子步長積分彈簧，步長跟 60 fps 每幀都更新的版本相同（原文的遊戲跑 60 fps）；差別是 100 ms 內的 6 個子步長用同一個陣風強度，這次沒有比較兩者的軌跡。

取消 `Timer` 要等陣風包絡為 0、彈簧的傾斜量與速度都小於 0.05。只看陣風包絡的話，樹身還在回彈時就停下來，畫面凍在傾斜的姿勢上。這次的設定沒有 `breeze`，`g` 為 0 時每一叢的位移只剩 `lean × 權重`，彈簧靜止就保證取整之後是 0；程式另外檢查位移全為 0，是給加了 `breeze` 的版本用的保險。

`timer ??=` 這一行讓動畫進行中再來的事件只重設 `eventAt`、不另起一個 `Timer`：事件比一陣風更密時，風會被延長，不會疊成好幾陣同時跑。另外，`Timer` 跟畫面的可見性無關。`TickerProviderStateMixin` 給的 `Ticker` 在頁面被不透明的路由蓋住時會被 `TickerMode` 靜音（`Overlay` 對被蓋住的 entry 設 `tickerEnabled: false`，3.41.3 的 `widgets/overlay.dart`），`Timer` 不會，所以實際的 App 裡，元件離開畫面或被蓋住時要自己取消 `Timer`：被路由蓋住可以用 `RouteAware` 的 `didPushNext`，App 進背景可以用 `AppLifecycleListener`，在對應的回呼裡 `cancel()`。App 進背景時 framework 本來就不排幀，沒取消的 `Timer` 浪費的是回呼的執行。這個 demo 只有一個畫面，`dispose()` 裡取消就夠。

`gust()` 在互動模式下接在場景的 `GestureDetector.onTap` 上，點樹就起一陣風；自動量測模式下，另一個 `Timer` 每 5 秒呼叫它一次，模擬一筆資料更新進來。5 秒是這次取的間隔（程式裡的常數 `kEventEverySeconds`，不能從指令列改），沒有比較其他值；間隔拉長時，eventDriven 每秒的平均幀數照比例下降，每一陣風的幀數不變。這個設定下，每 5 秒裡大約 4 秒在動，〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈資料小工具的重繪頻率與資料變化頻率〉說明了這個比例看起來跟一直擺動差不多。5 秒與 4 秒是為了讓 9 秒的計數窗碰到兩次事件、又量得到一整陣風的幀數，不是事件觸發設計的建議值；照那一篇把一陣縮到 1 秒以內時，每一陣約 10 幀，同樣 5 秒一次事件時平均約每秒 2 幀（從 `Timer` 的 100 ms 間隔推論，沒有實跑）。

eventDriven 沿用原文的週期相位與固定的左到右方向，是為了讓五種方式畫同一個姿勢、幀數可以比較；App 裡的事件動畫照同一篇的〈位置決定延遲〉，延遲改成元件到事件起點（被點的位置）的距離乘上固定的每單位延遲。

## 自動量測與 CPU 取樣

app 在 `--dart-define=AUTO=true` 時依序切換五種方式，每一種跑 12 秒（`MODE_SECONDS` 的預設值）。前 3 秒丟掉（`WARMUP_SECONDS` 的預設值）：切換之後的第一批 `FrameTiming` 可能還屬於上一種方式，profile 模式的批次間隔大約 100 ms，3 秒的餘裕也讓 `ps` 的 `%cpu`（下文說明它是衰減平均）先收斂一部分。之後 9 秒每秒記一次三個計數的增量，跑完印成一行 `PERSEC`，再印平均的 `RESULT` 行；五種都跑完之後印 `MODE done START <毫秒時間戳>` 與 `SUMMARY`，再 `exit(0)`。app 自己結束時，`flutter run` 印出 `Lost connection to device.`，這是正常結束。12 秒是這次取的長度，沒有比較其他值：

```bash
flutter run --profile -d macos --dart-define=AUTO=true
```

`--profile` 的理由在〈量測：framework frame、raster frame 與 paint 的計數器〉。`-d macos` 指定跑在本機桌面；接著其他裝置時，`flutter devices` 列得出可用的 id。跑的長度與暖機時間可以用 `--dart-define=MODE_SECONDS=20 --dart-define=WARMUP_SECONDS=5` 改。改短時注意事件間隔固定是 5 秒：`MODE_SECONDS` 減 `WARMUP_SECONDS` 的計數窗至少要涵蓋一次事件與它之後約 4 秒的一陣風，eventDriven 的平均才跟本篇的數字可比；計數窗只有 4 秒時，只碰得到一次事件的開頭，平均會低很多。

CPU 使用率在 app 外面取樣。等 app 視窗出現之後，另開一個 shell，每秒對 app 的行程跑一次 `ps`：

```bash
APP_PID=$(pgrep -f 'wind_sway_demo.app/Contents/MacOS/wind_sway_demo')
while kill -0 "$APP_PID" 2>/dev/null; do
  echo "$(date +%s) $(ps -p "$APP_PID" -o %cpu=)"
  sleep 1
done
```

`pgrep -f` 比對完整的命令列；`wind_sway_demo` 是建立專案時的 `--project-name`。視窗出現之前就跑的話，`pgrep` 找不到行程，`APP_PID` 是空值，迴圈不印任何一行就結束；之前用互動模式開的同一個 app 還沒關時，`pgrep` 會回兩個行程，`APP_PID` 有兩行，迴圈同樣立刻結束，先關掉另一個。macOS 的 `ps` 對 `%cpu` 的定義是「最多一分鐘內的衰減平均」（`man ps`），切換方式之後要好幾秒才收斂到新的值，而且讀數本身會跳動，所以這個數字只拿來比大小，不拿來當絕對的耗用量。要把取樣對到模式，把 log 裡每一行 `MODE <名稱> START <毫秒時間戳>` 的時間戳除以 1000、加上 `WARMUP_SECONDS`（預設 3），得到的秒數就是這個模式開始計數的那一秒，對應 CPU 迴圈印的 `date +%s`。

## 結果：兩次實測與預測的對照

量測之前寫下的預測：static 三個計數都接近 0；smooth 三個都等於螢幕更新率；tickerStepped 的繪製不超過每秒 10 次，而 framework frame 與 raster frame 仍等於螢幕更新率，因為 `Ticker` 每一次觸發都會排下一幀；timerStepped 三個都不超過每秒 10 次；eventDriven 的平均很低，只有起風那幾秒有幀。

橡樹與松樹那一輪兩次量測的 9 秒平均（每秒的次數，斜線前是第一次、後是第二次；平均每幀柵格化時間是 `RESULT` 行的 `avgRaster`，來自 `FrameTiming.rasterDuration`；CPU 欄是兩次量測全部讀數的最小值到最大值）：

| 驅動方式      | framework frame | raster frame  | paint         | 平均每幀柵格化時間 | CPU 取樣                              |
| ------------- | --------------- | ------------- | ------------- | ------------------ | ------------------------------------- |
| static        | 0 / 0           | 0 / 0         | 0 / 0         | 沒有幀             | 第一次 0% 到 18%，第二次 0%（見下文） |
| smooth        | 143.9 / 144.2   | 142.9 / 144.9 | 143.9 / 144.2 | 3.73 / 3.71 ms     | 58% 到 65%                            |
| tickerStepped | 144.2 / 144.3   | 143.6 / 143.9 | 9.7 / 9.7     | 3.89 / 3.99 ms     | 58% 到 68%                            |
| timerStepped  | 10.1 / 10.1     | 10.0 / 10.1   | 10.1 / 10.1   | 9.55 / 9.94 ms     | 11% 到 16%                            |
| eventDriven   | 5.1 / 5.1       | 5.0 / 4.9     | 5.1 / 5.1     | 10.0 / 10.3 ms     | 起風時 6% 到 16%，事件之間 0% 到 0.7% |

timerStepped 以外的四種方式，幀數都跟預測一致。timerStepped 的 10.1 略高於預測的上限：兩次的逐秒計數（`PERSEC` 行）各有一秒的 framework frame 是 11，9 秒共 91 次。100 ms 的 `Timer` 在 9 秒的計數窗裡觸發 90 或 91 次，取決於第一次觸發落在窗裡的哪個位置（推論），所以預測的上限應該寫成每秒 10 次左右。smooth 與 tickerStepped 的 raster frame，逐秒的值在 135 到 155 之間跳動，9 秒的總數跟 framework frame 相差不到一批（第一次 smooth 的 raster 對 framework：1286 對 1295）。從 profile 模式約 100 ms 一批推論，跳動來自一批回報跨過整秒邊界：100 ms 在 144 Hz 下約 14 幀，一秒多算或少算一批，就跟 144 相差 14 幀左右，跟 135 與 155 各自偏離 144 的 9 幀與 11 幀同一個量級。第一次的 static 沒有排任何一幀，CPU 取樣卻在 0% 到 18% 之間；第二次是 0%。第一次的讀數在 static 的計數窗開始之前已經是 0%，之後才升起來，所以不是啟動時的負載還沒衰減完。兩輪的四次量測（簡化樹那一輪的兩次也算在內），在 app 啟動後的前十幾秒裡都有幾秒讀數落在 8% 到 38% 之間，出現的時間不固定：這一輪的第一次，有一段落進了 static 的計數窗，其他三次都落在計數窗開始之前。這次沒有查出是行程裡的哪一段工作，候選有 Dart 的垃圾回收清掉啟動時建場景配置的物件，以及 `flutter run` 連上 VM service 之後發出的查詢（都是推論）。重做時把 static 排到最後，或拉長 static 開始計數之前的暖機秒數，可以避開這一段（推論，這次沒有改順序重跑）。

eventDriven 每秒的 framework frame 長這樣（第一次）：`0 0 7 10 7 4 0 8 10`。九個數字依序是切換到 eventDriven 之後的九個一秒區間：第一個是第 3 到第 4 秒，最後一個是第 11 到第 12 秒。自動量測的計時器在切換後第 5 秒與第 10 秒觸發事件，所以第三個數字（第 5 到第 6 秒）開始有幀。每一陣風持續大約 4 秒，陣風包絡本身 2.4 秒，之後是彈簧回彈到停止，包絡加回彈共 28 幀左右；兩陣之間是 0。第二陣在計數窗結束時還沒跑完。

### 跟簡化樹那一輪的對照

兩輪之間同時改了三件事：樹的造型（14 叢的簡化樹，換成 32 叢的橡樹加 9 層的松樹）、畫面的大小（288 × 336 邏輯點放大到 672 × 400）、繪製方式（每一幀逐格畫方塊，換成重播錄好的 `Picture`）。兩輪的場景在圖層樹裡都只有一個圖層，差在這個圖層裡要畫與要柵格化的內容。這三件事各自佔多少影響，這次沒有拆開量。

兩輪的 framework frame 與 raster frame 每秒次數相差在 6 次以內；跟姿勢變化次數有關的 paint 與 eventDriven 每一陣的幀數，橡樹與松樹那一輪比較多（tickerStepped 的 paint 9.2 對 9.7，eventDriven 每陣約 24 對 28 幀），原因這次沒有查。eventDriven 的 `Timer` 要等全部葉叢取整之後的位移都是 0 才停，葉叢從 14 叢變成 41 叢之後，這個條件比較晚成立，這是每陣幀數變多的一個候選（推論）。每一幀的 build 時間與柵格化時間都變了，CPU 取樣的讀數也跟著不同。下表的每幀 build 是 `RESULT` 行的 `avgBuild`，是 UI 執行緒處理一幀的時間（動畫回呼、rebuild、繪製與組圖層樹，範圍見 [FrameTiming](/programming/flutter/knowledge-cards/frame-timing/) 卡），前一張表的 paint 欄則是繪製的次數；每一格的斜線前是那一輪的第一次、斜線後是第二次；CPU 取樣是那一輪兩次量測全部讀數的最小值到最大值：

| 驅動方式      | 簡化樹：每幀 build | 簡化樹：每幀柵格化 | 簡化樹：CPU 取樣  | 橡樹與松樹：每幀 build | 橡樹與松樹：每幀柵格化 | 橡樹與松樹：CPU 取樣 |
| ------------- | ------------------ | ------------------ | ----------------- | ---------------------- | ---------------------- | -------------------- |
| smooth        | 1.37 / 1.59 ms     | 2.27 / 2.15 ms     | 多數秒 53% 到 68% | 0.38 / 0.38 ms         | 3.73 / 3.71 ms         | 58% 到 65%           |
| tickerStepped | 0.24 / 0.23 ms     | 2.56 / 2.25 ms     | 31% 到 60%        | 0.10 / 0.09 ms         | 3.89 / 3.99 ms         | 58% 到 68%           |
| timerStepped  | 1.54 / 1.50 ms     | 2.65 / 2.41 ms     | 3% 到 6%          | 1.02 / 1.13 ms         | 9.55 / 9.94 ms         | 11% 到 16%           |
| eventDriven   | 2.15 / 1.62 ms     | 3.52 / 2.75 ms     | 起風時 3% 到 7%   | 1.08 / 1.16 ms         | 10.0 / 10.3 ms         | 起風時 6% 到 16%     |

簡化樹那一輪的幀數（第一次與第二次）：smooth 每秒 144.2 與 139.2 幀，tickerStepped 144.3 與 143.9 幀、paint 兩次都是 9.2，timerStepped 兩次都是 9.8 幀，eventDriven 兩次都是 4.4 幀。那一版的程式沒有附在本篇，它跟附錄的差別就是上面那三件事。

- **tickerStepped 與 smooth 的 CPU 取樣差距消失**：簡化樹那一輪，tickerStepped 的取樣平均比 smooth 低約 12 個百分點（兩次平均 48% 對 60%），只有少數幾秒的 tickerStepped 讀數落進 smooth 的範圍；橡樹與松樹那一輪，兩者都落在 58% 到 68%。從 `avgBuild` 推論：tickerStepped 跟 smooth 比，每一幀省下的是 build 這一段（rebuild 與繪製），兩者每幀 build 的差乘上每秒 144 幀，就是每秒省下的 build 時間。簡化樹那一輪約 (1.48 − 0.24) × 144 ≈ 180 ms，相當於一個核心的 18%，跟取樣看到的約 12 個百分點同一個量級；橡樹與松樹那一輪繪製改成重播 `Picture`，smooth 每幀的 build 只剩 0.38 ms，約 (0.38 − 0.10) × 144 ≈ 41 ms，相當於一個核心的 4%，比兩者 58% 到 68% 的取樣範圍窄，所以分不出來。三件改動裡只有繪製方式會減少 Dart 端的繪製工作：造型與畫面都變大，照逐格畫的話，要畫的方塊數上限會從 48 × 56 = 2,688 格增加到 168 × 100 = 16,800 格。`ps` 量的是整個行程，這次沒有分執行緒量兩者各自的 CPU。
- **一直擺動的 smooth、tickerStepped、timerStepped 裡，timerStepped 仍然最省，省的比例變小**：CPU 取樣的平均（那一輪兩次量測全部讀數的平均，下同）從 smooth 的約 63% 降到約 13%，大約五分之一；簡化樹那一輪從約 60% 降到約 4.7%，大約十三分之一。可能的成因在下一條：橡樹與松樹那一輪低幀率時每一幀的柵格化比較長。
- **低幀率時，平均每幀的柵格化時間比較長**：timerStepped 與 eventDriven 每幀約 10 ms，smooth 與 tickerStepped 每幀約 4 ms；簡化樹那一輪是 2.4 到 3.5 ms 對 2.2 到 2.6 ms，差距小得多。這次沒有量原因，可能的成因有 GPU 在低負載時降頻、每一幀之間快取變冷（都是推論）。同一輪的每幀 build 也往同一個方向變：smooth 與 timerStepped 每一幀的工作相同（算姿勢、rebuild、重播 `Picture`），build 卻是 0.38 ms 對 1.02 到 1.13 ms。build 跑在 UI 執行緒上、不等 GPU，所以另一個候選是 CPU 在低負載時降頻，或把執行緒排到效率核心（推論，這次沒有量 CPU 頻率）；簡化樹那一輪兩者的 build 相近（1.37 到 1.59 ms 對 1.50 到 1.54 ms）。`rasterDuration` 是 raster 執行緒的牆鐘時間，含等 GPU 排程的時間，不等於 CPU 時間：Flutter 3.41.3 的 engine 原始碼裡，`rasterizer.cc` 的 raster 起訖包住整個繪製到 surface 的過程（`DrawToSurfaceUnsafe`），macOS 版送出畫面的 `FlutterSurfaceManager.mm` 的 `presentSurfaces` 會呼叫 Metal 的 `waitUntilScheduled`，等 command buffer 排進 GPU。把 build 與柵格化的牆鐘時間加起來、換算成每秒的量，兩輪各算一次：簡化樹那一輪 smooth 約 (1.48 + 2.21) × 144 ≈ 531 ms，timerStepped 約 (1.52 + 2.53) × 10 ≈ 41 ms，比值約十三分之一；橡樹與松樹那一輪約 590 ms 對 109 ms，約五分之一。兩輪的比值都跟各自 CPU 取樣的比例接近。這只表示每幀的牆鐘時間跟 CPU 取樣往同一個方向變化，不證明 CPU 主要花在柵格化；要確認，得分執行緒量（見〈未量測的範圍〉）。同一個場景把葉叢改成紋理圖集、背景改成點陣圖並獨立成圖層、換姿勢不 rebuild 之後（幾處一起量），低幀率與每個 vsync 都排幀的每幀柵格化縮到 0.7 到 0.9 ms 對 0.6 到 0.8 ms，build 的差距也幾乎消失，數字在〔[Flutter 像素場景的每幀柵格化成本](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)〕。

## 讀法：tickerStepped 的繪製次數與柵格化次數

tickerStepped 的繪製降到每秒 9.7 次，framework frame 與 raster frame 卻跟 smooth 一樣多。原因在 Flutter 的 `Ticker.scheduleTick()` 與 `RendererBinding.drawFrame()`：

- `Ticker.scheduleTick()` 每一次都呼叫 `SchedulerBinding.instance.scheduleFrame()`，所以一個啟動中的 `Ticker` 每個 vsync 都排一幀，不管它的回呼有沒有呼叫 `setState`。`scheduleFrame()` 在 Flutter 按需重繪裡的角色，寫在〔[Flutter scheduleFrame()：按需 render 的最底層原語](/work-log/flutter_schedule_frame/)〕。
- `RendererBinding.drawFrame()` 每次執行都依序跑 `flushLayout`、`flushCompositingBits`、`flushPaint`，再對每個 `RenderView` 呼叫 `compositeFrame()`，把圖層樹送給 engine 柵格化。沒有任何 render object 被標成 dirty 時，前三步幾乎不做事，`compositeFrame()` 仍然送出一幀。〔[Flutter 畫面落後邏輯狀態（log 正確、畫面不符）— 重繪訊號排查與心跳做法](/work-log/flutter_repaint_heartbeat/)〕的重繪心跳依賴的是同一個性質：定時排一幀，畫面就會重新合成。

tickerStepped 跟 smooth 每一幀做的工作，差在姿勢計算、rebuild 與繪製：smooth 每個 vsync 都做這三件事；tickerStepped 的 `Ticker` 回呼每個 vsync 也會執行一次，但距離上次換姿勢不到 100 ms 時直接返回，所以場景這一層一秒只重畫 9 到 10 次，整個畫面的合成與柵格化仍然一秒 144 次。兩者每一幀柵格化的是結構相同的圖層樹，平均每幀的柵格化時間也相近（tickerStepped 3.89 與 3.99 ms，smooth 3.73 與 3.71 ms）。CPU 取樣的範圍互相重疊（smooth 58% 到 65%，tickerStepped 58% 到 68%），所以在橡樹與松樹的場景裡，只減少繪製次數，CPU 的差別落在取樣的雜訊範圍內。這個場景的繪製是重播啟動時錄好的 `Picture`，錄製的成本在啟動時就付掉了：smooth 每幀的 build 是 0.38 ms，只佔每幀時間的一小段；3.7 ms 的柵格化是牆鐘時間，含等 GPU 排程的時間，CPU 花在哪一段要分執行緒量（見〈未量測的範圍〉）；繪製時要即時計算大量 path、模糊或 shader 的插圖，減少繪製省下的時間會比這裡多，這次沒有量。同樣的寫法（每個 vsync 都醒、沒到間隔就返回）用在瀏覽器 canvas 的 `requestAnimationFrame` 迴圈上，CPU 降了一半，量測在〔[瀏覽器 canvas 像素動畫的 CPU 量測與重畫上限](/ux-design/06-interaction-feedback/hands-on/canvas-ambient-frame-cap/)〕的〈在動畫迴圈加上重畫上限，流星飛過時解除〉。

把驅動器換成 `Timer`（timerStepped）之後，沒有任何驅動器在每個 vsync 排幀，三個計數一起降到每秒 10 次左右，在橡樹與松樹的場景，CPU 取樣降到約五分之一（簡化樹那一輪約十三分之一，兩輪的差別在〈跟簡化樹那一輪的對照〉）。事件觸發的版本再把事件之間的那幾秒也降到 0。低頻驅動省下渲染管線次數的這個結果，對照遊戲引擎與[按需重繪](/ux-design/knowledge-cards/on-demand-rendering/)的 UI 框架的差別，寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈重繪成本與動畫驅動器的排幀頻率〉。同一個場景改繪製方式、把每幀柵格化從約 3.7 ms 降到約 0.6 ms 之後，timerStepped 對 smooth 的 CPU 取樣比例約十分之一，改法與量測在〔[Flutter 像素場景的每幀柵格化成本](/programming/flutter/hands-on/pixel-scene-texture-atlas-frame-cost/)〕。

## 未量測的範圍：手機耗電、60 Hz 螢幕、合成器動畫、執行緒拆分

- **手機的耗電**：這次只量了桌面的幀數與 CPU 取樣。手機上要用 Xcode Instruments 的 Energy Log 或 Android Studio 的 Power Profiler 量，這次在桌面上量不到 GPU 與螢幕的耗電。
- **60 Hz 螢幕上的差距**：smooth 與 tickerStepped 的幀數會降到每秒 60 次左右，timerStepped 與 eventDriven 不受螢幕更新率影響，所以前兩種與 timerStepped 的幀數比會從 144 ÷ 10.1 ≈ 14 倍縮小到 60 ÷ 10.1 ≈ 6 倍（從機制推論，這次沒有在 60 Hz 螢幕上跑）。CPU 的差距會比幀數比小，原因同〈跟簡化樹那一輪的對照〉裡低幀率時每幀柵格化比較長那一條（推論）。
- **合成器動畫**：Flutter 的動畫由 framework 在 Dart 端每幀驅動，沒有交給平台合成器的路徑，所以這次沒有對照 CSS `transform` 動畫或 Core Animation 的版本。
- **減少動態的設定**：這個 demo 沒有讀減少動態的設定；實際的 App 在 `MediaQuery.disableAnimationsOf(context)` 為 true 時，不起陣風，或只換顏色（〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈減少動態的系統設定與 WCAG 2.2.2〉）。
- **macOS 的 merged thread**：這次的 Flutter 在 macOS 上預設把 UI 執行緒與平台執行緒合併（各執行緒負責什麼見 [Flutter Thread Model](/programming/flutter/knowledge-cards/flutter-thread-model/)）（啟動 log 印出 `Running with merged UI and platform thread. Experimental.`），合併之後，Dart 的 build 與平台的事件處理跑在同一條執行緒上，柵格化在另一條 raster 執行緒上（從 log 的訊息與 Flutter 的執行緒模型推論）；`ps` 量到的是整個行程的 CPU，不分執行緒。要分清 build 與柵格化各自用掉多少 CPU，要用 DevTools 的 timeline 或 Xcode Instruments，這次沒有做。

## 附錄：完整的 `lib/main.dart`

整份取代 `flutter create` 產生的 `lib/main.dart`。互動模式（`flutter run -d macos`）用畫面下方的 chip 切換驅動方式，eventDriven 時點樹起一陣風；自動量測照〈自動量測與 CPU 取樣〉的指令跑。

```dart
// 像素樹風吹動畫：五種驅動方式的重繪成本比較。
//
// 五種驅動方式下 app 畫同一個場景、用同一個運動模型（位置決定相位的行進波、
// 中心穩邊緣鬆、整數像素位移），差別只在「誰叫 Flutter 排 frame、多常排」：
//
//   static         不動，基準線
//   smooth         AnimationController 每個 vsync 算一次、位移不取整
//   tickerStepped  Ticker 每個 vsync 跑，姿勢 100ms 才變一次（原文的驅動結構，省掉彈簧）
//   timerStepped   Timer 每 100ms 算一次姿勢，有變才 setState
//   eventDriven    平常靜止；事件（點擊或模擬的資料更新）來了才起一陣風，
//                  風停、樹回正之後 Timer 自己取消
//
// 場景由程式產生（不用圖檔），並排兩棵樹：
//   橡樹  32 叢不規則的圓形葉叢由後往前疊，光從左上來，色相由左往右從黃綠變藍綠，
//         每個像素帶一點雜訊；樹幹往上收窄，底部的根往外撐開，枝幹伸進樹冠。
//   松樹  九層往下垂的枝層，上層蓋在下層上面，每一層上亮下暗、下緣是鋸齒狀的針葉；
//         越高的層權重越大、擺得越多。原文的松樹幹用 shader 逐列平移做出彎曲，
//         這裡樹幹不動，只讓枝層擺動。
// 每一叢（每一層）在啟動時錄成一張 ui.Picture（相當於原文的「每一叢一張 sprite」），
// 每一幀只把這些 Picture 平移後重畫。
//
// 自動量測：flutter run --profile -d macos --dart-define=AUTO=true
// 每種方式跑 MODE_SECONDS 秒，丟掉前 WARMUP_SECONDS 秒，印出每秒的
// framework frame 數、raster frame 數（FrameTiming）、paint 次數，跑完 exit(0)。
//
// 部落格實作文章的附錄與橡樹與松樹那一輪量測對應這個版本；簡化樹那一輪
// 用的是一棵 48 × 56 格、橢圓切成 14 叢、每一幀逐格畫方塊的樹。
import 'dart:async';
import 'dart:io' show exit;
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

const bool kAuto = bool.fromEnvironment('AUTO');
const int kModeSeconds = int.fromEnvironment('MODE_SECONDS', defaultValue: 12);
const int kWarmupSeconds = int.fromEnvironment('WARMUP_SECONDS', defaultValue: 3);

/// 事件驅動模式在自動量測時，每隔幾秒模擬一次資料更新。
const int kEventEverySeconds = 5;

/// 姿勢的更新間隔（原文 POSE_TIME := 0.1）。
const Duration kPoseInterval = Duration(milliseconds: 100);

/// 背景色（深青綠，跟原文截圖的背景接近）。
const Color kBackground = Color(0xFF233838);

enum Mode { static, smooth, tickerStepped, timerStepped, eventDriven }

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  Stats.instance.install();
  runApp(const DemoApp());
}

// ---------------------------------------------------------------------------
// 量測
// ---------------------------------------------------------------------------

class Stats {
  Stats._();
  static final Stats instance = Stats._();

  int frameworkFrames = 0; // drawFrame 被呼叫的次數
  int rasterFrames = 0; // engine 回報的 FrameTiming 數
  int paints = 0; // 場景的 CustomPainter.paint 次數
  int rasterMicros = 0;
  int buildMicros = 0;

  void install() {
    SchedulerBinding.instance.addPersistentFrameCallback((_) => frameworkFrames++);
    SchedulerBinding.instance.addTimingsCallback((timings) {
      rasterFrames += timings.length;
      for (final t in timings) {
        rasterMicros += t.rasterDuration.inMicroseconds;
        buildMicros += t.buildDuration.inMicroseconds;
      }
    });
  }

  void reset() {
    frameworkFrames = 0;
    rasterFrames = 0;
    paints = 0;
    rasterMicros = 0;
    buildMicros = 0;
  }
}

// ---------------------------------------------------------------------------
// 調色盤與雜訊
// ---------------------------------------------------------------------------

/// 每一條色階由暗到亮五階，整體偏暗、偏橄欖色。葉子的色相在三條色階之間內插。
const List<Color> kYellowRamp = [
  Color(0xFF29280F),
  Color(0xFF4B4719),
  Color(0xFF746B26),
  Color(0xFF9C8D3A),
  Color(0xFFBFAE4E),
];
const List<Color> kGreenRamp = [
  Color(0xFF1A2814),
  Color(0xFF304626),
  Color(0xFF4A6433),
  Color(0xFF678042),
  Color(0xFF879D56),
];
const List<Color> kTealRamp = [
  Color(0xFF122228),
  Color(0xFF20383B),
  Color(0xFF31504C),
  Color(0xFF4A695F),
  Color(0xFF668274),
];
const List<Color> kBarkRamp = [
  Color(0xFF1E130D),
  Color(0xFF3B2618),
  Color(0xFF573B27),
  Color(0xFF735238),
  Color(0xFF8E6B4C),
];

/// 色相 t：0 是黃綠、0.5 是綠、1 是藍綠；shade：0 到 4 由暗到亮。
Color leafColor(double t, int shade) {
  t = t.clamp(0.0, 1.0);
  if (t < 0.5) return Color.lerp(kYellowRamp[shade], kGreenRamp[shade], t * 2)!;
  return Color.lerp(kGreenRamp[shade], kTealRamp[shade], (t - 0.5) * 2)!;
}

Color darken(Color c, double k) =>
    Color.from(alpha: 1, red: c.r * k, green: c.g * k, blue: c.b * k);

/// 固定的整數雜湊，回傳 0 到 1。同一個座標每次算出同一個值，樹每次啟動都長一樣。
double hash(int x, int y, int seed) {
  var h = x * 374761393 + y * 668265263 + seed * 982451653;
  h = (h ^ (h >> 13)) * 1274126177;
  h = h ^ (h >> 16);
  return (h & 0xffff) / 65535.0;
}

// ---------------------------------------------------------------------------
// 場景：程式產生的兩棵像素樹，拆成背景層（內層、樹幹、枝幹、根、草）與會動的葉叢
// ---------------------------------------------------------------------------

class Clump {
  Clump(this.picture, this.cx, this.cy, this.weight);
  final ui.Picture picture; // 這一叢的像素，座標單位是格（場景座標）
  final double cx; // 葉叢中心（格）
  final double cy;
  final double weight; // 中心或下層小、邊緣或上層大，0.35 到 1.0
}

/// 繪製時的小工具：在格座標上畫一格。
class _Pen {
  final Paint paint = Paint()..isAntiAlias = false;
  void px(Canvas c, int x, int y, Color color) {
    paint.color = color;
    c.drawRect(Rect.fromLTWH(x.toDouble(), y.toDouble(), 1, 1), paint);
  }
}

class Tree {
  Tree._(this.back, this.clumps);
  final ui.Picture back; // 不會動的部分
  final List<Clump> clumps; // 依繪製順序排列（後面的蓋在前面的上面）

  static const int width = 168;
  static const int height = 100;

  /// 每一格畫成幾個邏輯點。
  static const double cell = 4;

  static Tree build() {
    final pen = _Pen();
    final rec = ui.PictureRecorder();
    final back = Canvas(rec);
    final clumps = <Clump>[];
    _buildOak(back, clumps, pen, ox: 6, groundY: height - 2);
    _buildPine(back, clumps, pen, cx: 136, groundY: height - 2);
    return Tree._(rec.endRecording(), clumps);
  }

  // --- 樹幹、枝幹與根共用：把一組格子依明暗值畫成樹皮 ---
  static void _drawBark(Canvas c, _Pen pen, Map<int, double> cells, int seed) {
    for (final e in cells.entries) {
      final x = e.key % width, y = e.key ~/ width;
      final edge = !cells.containsKey(e.key - 1) || !cells.containsKey(e.key + 1);
      if (edge) {
        pen.px(c, x, y, kBarkRamp[0]);
        continue;
      }
      // 樹皮：直條紋（只看 x 的雜訊）加每格的細雜訊。
      final v = e.value + (hash(x, 0, seed) - 0.5) * 0.4 + (hash(x, y, seed + 1) - 0.5) * 0.25;
      pen.px(c, x, y, kBarkRamp[(v * 4).round().clamp(1, 4)]);
    }
  }

  /// 從 (x0, y0) 到 (x1, y1) 的粗線，寬度由 w0 漸變到 w1；明暗左亮右暗。
  static void _limb(Map<int, double> cells, double x0, double y0, double x1, double y1, double w0, double w1) {
    const steps = 48;
    for (var i = 0; i <= steps; i++) {
      final t = i / steps;
      final x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t, w = w0 + (w1 - w0) * t;
      for (var yy = (y - w).floor(); yy <= y + w; yy++) {
        for (var xx = (x - w).floor(); xx <= x + w; xx++) {
          if (xx < 0 || yy < 0 || xx >= width || yy >= height) continue;
          final dx = xx + 0.5 - x, dy = yy + 0.5 - y;
          if (dx * dx + dy * dy <= w * w) {
            cells.putIfAbsent(yy * width + xx, () => (0.5 - 0.35 * dx / w).clamp(0.0, 1.0));
          }
        }
      }
    }
  }

  static void _grass(Canvas c, _Pen pen, int x0, int x1, int y, int seed) {
    for (var x = x0; x < x1; x++) {
      if (hash(x, 1, seed) > 0.5) {
        pen.px(c, x, y, leafColor(0.35, 1 + (hash(x, 2, seed) * 2).round()));
        if (hash(x, 3, seed) > 0.55) pen.px(c, x, y - 1, leafColor(0.3, 2 + (hash(x, 4, seed) * 2).round()));
      }
    }
  }

  // -------------------------------------------------------------------------
  // 橡樹
  // -------------------------------------------------------------------------

  static void _buildOak(Canvas back, List<Clump> clumps, _Pen pen, {required int ox, required int groundY}) {
    final rnd = math.Random(7);
    final cx = ox + 50.0; // 樹的中線
    const canopyCy = 36.0; // 樹冠中心（權重的參考點）

    // 葉叢的位置：由上往下七排，排成扁寬的半球；排與排、叢與叢之間留一點縫。
    final specs = <({double x, double y, double r})>[];
    const rows = [
      (y: 15.0, half: 12.0, n: 3),
      (y: 22.0, half: 23.0, n: 4),
      (y: 29.0, half: 32.0, n: 5),
      (y: 36.0, half: 38.0, n: 6),
      (y: 43.0, half: 39.0, n: 6),
      (y: 50.0, half: 34.0, n: 5),
      (y: 56.0, half: 24.0, n: 3),
    ];
    for (final row in rows) {
      for (var i = 0; i < row.n; i++) {
        final x = cx - row.half + 2 * row.half * i / (row.n - 1) + (rnd.nextDouble() - 0.5) * 3;
        final y = row.y + (rnd.nextDouble() - 0.5) * 2.5;
        specs.add((x: x, y: y, r: 6.6 + rnd.nextDouble() * 1.6));
      }
    }
    // 上面的排先畫、下面的排後畫，下排疊在上排前面。
    specs.sort((a, b) => a.y.compareTo(b.y));

    final blobs = <Set<int>>[];
    final canopy = <int>{};
    for (var i = 0; i < specs.length; i++) {
      final s = specs[i];
      final p1 = rnd.nextDouble() * 6.28, p2 = rnd.nextDouble() * 6.28, p3 = rnd.nextDouble() * 6.28;
      final cells = <int>{};
      final r = s.r.ceil() + 2;
      for (var y = (s.y - r).floor(); y <= s.y + r; y++) {
        for (var x = (s.x - r).floor(); x <= s.x + r; x++) {
          if (x < 0 || y < 0 || x >= width || y >= height) continue;
          final dx = x + 0.5 - s.x, dy = y + 0.5 - s.y;
          final a = math.atan2(dy, dx);
          // 圓形加三個低頻的正弦起伏，再加每格的雜訊讓邊緣毛躁。
          final edge = s.r * (1 + 0.10 * math.sin(3 * a + p1) + 0.07 * math.sin(5 * a + p2) + 0.05 * math.sin(7 * a + p3));
          if (math.sqrt(dx * dx + dy * dy) <= edge + (hash(x, y, 100 + i) - 0.5) * 1.4) cells.add(y * width + x);
        }
      }
      blobs.add(cells);
      canopy.addAll(cells);
    }

    // 內層：整個樹冠往內縮兩格、顏色乘 0.45 的暗色版本，葉叢之間的縫與葉叢移開時露出來。
    Set<int> erode(Set<int> s) => {
          for (final k in s)
            if (s.contains(k - 1) && s.contains(k + 1) && s.contains(k - width) && s.contains(k + width)) k,
        };
    for (final key in erode(erode(canopy))) {
      final x = key % width, y = key ~/ width;
      pen.px(back, x, y, darken(leafColor((x - ox - 18) / 64, 1), 0.45));
    }

    // 樹幹、枝幹與根。
    final bark = <int, double>{};
    for (var y = 56; y <= groundY; y++) {
      final c = cx + 0.5 * math.sin(y / 8.0);
      // 往下漸寬，最後十格往外撐開成根部。
      var half = 3.8 + (y - 56) * 0.05;
      final flare = (y - (groundY - 10)) / 10;
      if (flare > 0) half += flare * flare * 9;
      for (var x = (c - half - 1).floor(); x <= c + half + 1; x++) {
        final rel = (x + 0.5 - c) / half;
        // 根部的邊緣用雜訊切出幾條根的輪廓。
        final rough = flare > 0 ? (hash(x, y, 31) - 0.5) * 0.3 * flare : 0.0;
        if (rel.abs() <= 1 + rough) bark[y * width + x] = (0.6 - 0.38 * rel).clamp(0.0, 1.0);
      }
    }
    // 兩條往外伸、貼著地面的根。
    _limb(bark, cx - 8, groundY - 3.0, cx - 19, groundY - 0.5, 1.8, 0.8);
    _limb(bark, cx + 8, groundY - 3.0, cx + 20, groundY - 0.5, 1.8, 0.8);
    // 枝幹：樹幹在樹冠下方分岔，兩根主枝露在下排葉叢之間，其餘伸進樹冠被葉叢蓋住。
    for (final (x1, y1, w) in [(-13.0, 50.0, 2.6), (14.0, 51.0, 2.6), (-26.0, 40.0, 2.0), (27.0, 41.0, 2.0), (1.0, 30.0, 1.8)]) {
      _limb(bark, cx + x1 * 0.1, 68, cx + x1, y1, w, 1.1);
    }
    _drawBark(back, pen, bark, 41);
    _grass(back, pen, (cx - 26).round(), (cx + 26).round(), groundY, 53);

    // 葉叢：每一叢錄成一張 Picture。
    for (var i = 0; i < specs.length; i++) {
      final s = specs[i];
      final cells = blobs[i];
      // 色相：依整棵樹的左右位置，加一點每叢自己的偏移，讓相鄰兩叢的色調分得開。
      final tone = (s.x - ox - 18) / 64 + (rnd.nextDouble() - 0.5) * 0.2;
      final rec = ui.PictureRecorder();
      final c = Canvas(rec);
      bool has(int x, int y) => cells.contains(y * width + x);
      for (final key in cells) {
        final x = key % width, y = key ~/ width;
        final nx = (x + 0.5 - s.x) / s.r, ny = (y + 0.5 - s.y) / s.r;
        // 輪廓：右邊或下面沒有自己的格子 → 最暗；左邊或上面沒有 → 次暗。
        if (!has(x + 1, y) || !has(x, y + 1)) {
          pen.px(c, x, y, leafColor(tone, 0));
          continue;
        }
        if (!has(x - 1, y) || !has(x, y - 1)) {
          pen.px(c, x, y, leafColor(tone, 1));
          continue;
        }
        // 光從左上來：越靠左上越亮、越靠邊緣與下緣越暗；每格再加雜訊做出斑駁的葉面。
        final light = (0.5 - 0.65 * (0.5 * nx + 0.87 * ny)).clamp(0.0, 1.0);
        final rim = math.sqrt(nx * nx + ny * ny);
        final v = 0.05 + 0.8 * light - 0.3 * rim + (hash(x, y, 7 + i) - 0.5) * 0.6;
        pen.px(c, x, y, leafColor(tone + 0.1 * nx, (v * 4).round().clamp(1, 4)));
      }
      final d = math.sqrt(math.pow(s.x - cx, 2) + math.pow(s.y - canopyCy, 2));
      clumps.add(Clump(rec.endRecording(), s.x, s.y, 0.35 + 0.65 * math.min(1.0, d / 34)));
    }
  }

  // -------------------------------------------------------------------------
  // 松樹
  // -------------------------------------------------------------------------

  static void _buildPine(Canvas back, List<Clump> clumps, _Pen pen, {required double cx, required int groundY}) {
    // 樹幹：細長、往下略寬，底部分出幾條短根。
    final bark = <int, double>{};
    _limb(bark, cx, 26, cx, groundY - 3.0, 1.1, 2.4);
    for (final (tx, w) in [(-9.0, 1.4), (-4.0, 1.1), (4.0, 1.1), (9.0, 1.4)]) {
      _limb(bark, cx + tx * 0.15, groundY - 6.0, cx + tx, groundY - 0.5, w + 0.5, 0.7);
    }
    _drawBark(back, pen, bark, 61);
    _grass(back, pen, (cx - 12).round(), (cx + 12).round(), groundY, 67);

    // 枝層：由上往下九層，越往下越寬。每一層是一個往下垂的裙形：
    // 上窄下寬、下緣有鋸齒狀的針葉；上半偏亮偏黃，下緣是暗藍綠的陰影。
    const tiers = 9;
    final specs = <({double top, double h, double half})>[];
    for (var i = 0; i < tiers; i++) {
      final t = i / (tiers - 1); // 0 是最上層
      final top = 9.0 + i * 7.4;
      specs.add((top: top, h: 5.0 + t * 3, half: 3.0 + t * 13.5));
    }
    final topY = specs.first.top, bottomY = specs.last.top + specs.last.h;
    // 下層先畫、上層後畫，上層的下緣蓋在下層的上半部。
    for (var i = tiers - 1; i >= 0; i--) {
      final s = specs[i];
      final seed = 200 + i;
      final cells = <int>{};
      for (var y = s.top.floor(); y <= (s.top + s.h + 3).ceil(); y++) {
        final r = (y - s.top) / s.h; // 0 到 1 是枝層本體，大於 1 是垂下的針葉
        for (var x = (cx - s.half - 3).floor(); x <= cx + s.half + 3; x++) {
          final dx = (x + 0.5 - cx).abs();
          if (r < 0) continue;
          if (r <= 1) {
            // 本體：上窄下寬，邊緣往下彎；邊緣加雜訊。
            final half = s.half * (0.2 + 0.8 * math.pow(r, 0.7));
            if (dx <= half + (hash(x, y, seed) - 0.5) * 2.2) cells.add(y * width + x);
          } else {
            // 下緣的針葉：一束一束往下垂，中間短、外側長。
            final tuft = hash(x ~/ 2, 0, seed) > 0.35;
            final len = 1 + 2.2 * (dx / s.half) + hash(x, 1, seed) * 1.5;
            if (tuft && dx <= s.half && (r - 1) * s.h <= len) cells.add(y * width + x);
          }
        }
      }
      final tone = 0.32 + 0.22 * (i / (tiers - 1)); // 上層偏黃綠、下層偏綠
      final rec = ui.PictureRecorder();
      final c = Canvas(rec);
      bool has(int x, int y) => cells.contains(y * width + x);
      for (final key in cells) {
        final x = key % width, y = key ~/ width;
        final r = (y - s.top) / s.h;
        final nx = (x + 0.5 - cx) / s.half;
        if (!has(x, y + 1) || !has(x + 1, y)) {
          pen.px(c, x, y, leafColor(tone + 0.25, 0)); // 下緣與右緣：暗藍綠的陰影
          continue;
        }
        if (!has(x - 1, y) || !has(x, y - 1)) {
          pen.px(c, x, y, leafColor(tone, 1));
          continue;
        }
        // 上半與左側亮、下半與右側暗；橫向的條紋雜訊做出一排排針葉的質感。
        final v = 0.85 - 0.75 * r - 0.25 * nx + (hash(x, y, seed + 50) - 0.5) * 0.5 + (hash(0, y, seed + 51) - 0.5) * 0.2;
        pen.px(c, x, y, leafColor(tone + 0.2 * r, (v * 4).round().clamp(1, 4)));
      }
      final height01 = 1 - (s.top - topY) / (bottomY - topY); // 上層接近 1
      clumps.add(Clump(rec.endRecording(), cx, s.top + s.h / 2, 0.35 + 0.65 * height01));
    }
  }
}

// ---------------------------------------------------------------------------
// 運動模型
// ---------------------------------------------------------------------------

/// 一陣風的時間包絡：事件發生後 [duration] 秒內從 0 升到 1 再落回 0。
double gustEnvelope(double sinceEvent, {double duration = 2.4}) {
  if (sinceEvent < 0 || sinceEvent > duration) return 0;
  return math.sin(math.pi * sinceEvent / duration);
}

class Spring {
  // 原文橡樹的參數：push 2.2、spring_period 2.2 s、damping 0.35。
  double lean = 0;
  double speed = 0;
  static const double push = 2.2;
  static const double period = 2.2;
  static const double damping = 0.35;

  void step(double gust, double dt) {
    final k = 2 * math.pi / period;
    speed += (k * k * (push * gust - lean) - 2 * damping * k * speed) * dt;
    lean += speed * dt;
  }

  bool get settled => lean.abs() < 0.05 && speed.abs() < 0.05;
}

/// 算出每一叢葉子的位移（單位是格）。[quantize] 為 true 時取整數格。
List<Offset> computePose(Tree tree, double t, double breeze, double gust, double lean, {required bool quantize}) {
  return [
    for (final c in tree.clumps)
      () {
        final along = c.cx + 0.25 * c.cy;
        final a = 2 * math.pi * (t / 1.54 - along / 69);
        final w = c.weight;
        final ride = lean * w;
        final dx = ride + w * (0.9 * breeze + 1.3 * gust) * (0.5 - 0.5 * math.cos(a));
        final dy = -w * (0.75 * breeze + 0.5 * gust) * math.max(math.sin(a), 0);
        return quantize ? Offset(dx.roundToDouble(), dy.roundToDouble()) : Offset(dx, dy);
      }(),
  ];
}

bool samePose(List<Offset> a, List<Offset> b) {
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// 畫場景
// ---------------------------------------------------------------------------

class TreePainter extends CustomPainter {
  TreePainter(this.tree, this.pose);
  final Tree tree;
  final List<Offset> pose;

  @override
  void paint(Canvas canvas, Size size) {
    Stats.instance.paints++;
    canvas.scale(size.width / Tree.width);
    canvas.drawPicture(tree.back);
    for (var i = 0; i < tree.clumps.length; i++) {
      canvas.save();
      canvas.translate(pose[i].dx, pose[i].dy);
      canvas.drawPicture(tree.clumps[i].picture);
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(TreePainter old) => !samePose(old.pose, pose);
}

// ---------------------------------------------------------------------------
// 五種驅動方式
// ---------------------------------------------------------------------------

/// 持續的微風強度（smooth、tickerStepped、timerStepped 用）。
/// 原文的 breeze 是陣風周圍的弱風場、陣風之間落回 0；這裡固定成常數，
/// 是為了量「一直在動」的成本，跟原文不同。
const double kBreeze = 0.8;

class SwayTree extends StatefulWidget {
  const SwayTree({super.key, required this.mode, required this.tree});
  final Mode mode;
  final Tree tree;

  @override
  State<SwayTree> createState() => SwayTreeState();
}

class SwayTreeState extends State<SwayTree> with TickerProviderStateMixin {
  late List<Offset> pose = List.filled(widget.tree.clumps.length, Offset.zero);
  final Stopwatch clock = Stopwatch()..start();
  AnimationController? controller;
  Ticker? ticker;
  Timer? timer;
  Timer? autoEvents;
  Duration lastPoseAt = Duration.zero;
  final Spring spring = Spring();
  double? eventAt; // 秒，事件驅動模式最近一次事件的時間

  double get t => clock.elapsedMicroseconds / 1e6;

  @override
  void initState() {
    super.initState();
    switch (widget.mode) {
      case Mode.static:
        break;
      case Mode.smooth:
        controller = AnimationController(vsync: this, duration: const Duration(seconds: 1))
          ..addListener(() => setState(() {
                pose = computePose(widget.tree, t, kBreeze, 0, 0, quantize: false);
              }))
          ..repeat();
      case Mode.tickerStepped:
        ticker = createTicker((elapsed) {
          if (elapsed - lastPoseAt < kPoseInterval) return; // 每個 vsync 都進來，大多直接返回
          lastPoseAt = elapsed;
          final next = computePose(widget.tree, t, kBreeze, 0, 0, quantize: true);
          if (!samePose(next, pose)) setState(() => pose = next);
        })
          ..start();
      case Mode.timerStepped:
        timer = Timer.periodic(kPoseInterval, (_) {
          final next = computePose(widget.tree, t, kBreeze, 0, 0, quantize: true);
          if (!samePose(next, pose)) setState(() => pose = next);
        });
      case Mode.eventDriven:
        if (kAuto) {
          autoEvents = Timer.periodic(const Duration(seconds: kEventEverySeconds), (_) => gust());
        }
    }
  }

  /// 事件驅動模式：起一陣風。風停、彈簧回正、葉叢都回到 0 之後取消 Timer。
  void gust() {
    if (widget.mode != Mode.eventDriven) return;
    eventAt = t;
    timer ??= Timer.periodic(kPoseInterval, (_) {
      final since = t - eventAt!;
      final g = gustEnvelope(since);
      // 彈簧用 1/60 s 的子步長積分，畫面只在 100ms 的姿勢時刻更新。
      for (var i = 0; i < 6; i++) {
        spring.step(g, 1 / 60);
      }
      final next = computePose(widget.tree, t, 0, g, spring.lean, quantize: true);
      final rest = g == 0 && spring.settled && next.every((o) => o == Offset.zero);
      if (!samePose(next, pose)) setState(() => pose = next);
      if (rest) {
        timer?.cancel();
        timer = null;
      }
    });
  }

  @override
  void dispose() {
    controller?.dispose();
    ticker?.dispose();
    timer?.cancel();
    autoEvents?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: gust,
      child: RepaintBoundary(
        child: CustomPaint(
          size: const Size(Tree.width * Tree.cell, Tree.height * Tree.cell),
          painter: TreePainter(widget.tree, pose),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// App 與自動量測
// ---------------------------------------------------------------------------

class DemoApp extends StatefulWidget {
  const DemoApp({super.key});

  @override
  State<DemoApp> createState() => _DemoAppState();
}

class _DemoAppState extends State<DemoApp> {
  final Tree tree = Tree.build();
  Mode mode = Mode.static;
  final List<String> summary = [];

  @override
  void initState() {
    super.initState();
    if (kAuto) unawaited(runAuto());
  }

  Future<void> runAuto() async {
    await Future<void>.delayed(const Duration(seconds: 2));
    for (final m in Mode.values) {
      setState(() => mode = m);
      // ignore: avoid_print
      print('MODE ${m.name} START ${DateTime.now().millisecondsSinceEpoch}');
      await Future<void>.delayed(const Duration(seconds: kWarmupSeconds));
      Stats.instance.reset();
      final perSecond = <String>[];
      for (var s = kWarmupSeconds; s < kModeSeconds; s++) {
        final before = (Stats.instance.frameworkFrames, Stats.instance.rasterFrames, Stats.instance.paints);
        await Future<void>.delayed(const Duration(seconds: 1));
        perSecond.add('${Stats.instance.frameworkFrames - before.$1}/${Stats.instance.rasterFrames - before.$2}/${Stats.instance.paints - before.$3}');
      }
      final secs = kModeSeconds - kWarmupSeconds;
      final st = Stats.instance;
      final line = '${m.name.padRight(14)} framework ${(st.frameworkFrames / secs).toStringAsFixed(1)}/s'
          '  raster ${(st.rasterFrames / secs).toStringAsFixed(1)}/s'
          '  paint ${(st.paints / secs).toStringAsFixed(1)}/s'
          '  avgRaster ${st.rasterFrames == 0 ? '-' : (st.rasterMicros / st.rasterFrames / 1000).toStringAsFixed(2)}ms'
          '  avgBuild ${st.rasterFrames == 0 ? '-' : (st.buildMicros / st.rasterFrames / 1000).toStringAsFixed(2)}ms';
      // ignore: avoid_print
      print('PERSEC ${m.name} framework/raster/paint: ${perSecond.join(' ')}');
      // ignore: avoid_print
      print('RESULT $line');
      summary.add(line);
    }
    // ignore: avoid_print
    print('MODE done START ${DateTime.now().millisecondsSinceEpoch}');
    // ignore: avoid_print
    print('SUMMARY\n${summary.join('\n')}');
    await Future<void>.delayed(const Duration(milliseconds: 500));
    exit(0);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(brightness: Brightness.dark, colorSchemeSeed: const Color(0xFF4A6433)),
      home: Scaffold(
        backgroundColor: kBackground,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SwayTree(key: ValueKey(mode), mode: mode, tree: tree),
              const SizedBox(height: 12),
              Text(kAuto ? '自動量測：${mode.name}' : '模式：${mode.name}（eventDriven 時點樹起風）'),
              const SizedBox(height: 8),
              if (!kAuto)
                Wrap(
                  spacing: 8,
                  children: [
                    for (final m in Mode.values)
                      ChoiceChip(
                        label: Text(m.name),
                        selected: m == mode,
                        onSelected: (_) => setState(() => mode = m),
                      ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}
```
