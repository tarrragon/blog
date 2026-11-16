---
title: "Flutter 裝飾性動畫的驅動方式比較：AnimationController、Ticker、Timer 與事件觸發的 frame 數與 CPU 量測"
date: 2026-11-16
description: "在 Flutter 裡做一個會隨風擺動的裝飾元件，想知道 AnimationController、Ticker、Timer 與事件觸發各自讓渲染管線一秒跑幾次時讀：可重做的量測 app 與完整程式碼、FrameTiming 與 paint 次數的取法、144 Hz 螢幕上的實測結果與讀法。"
weight: 1
tags: ["flutter", "animation", "rendering", "performance", "hands-on"]
---

2026-11-16 在一台 macOS 15（Darwin 24.3）的 Mac 上做的量測：Flutter 3.41.3（Dart 3.11.1），以 profile 模式跑 macOS 桌面版，app 視窗開在一台更新率 144 Hz 的外接螢幕上。當時在驗證一個預期：把像素遊戲裡「樹被風吹動」的做法搬進 App 時，姿勢一秒只換 10 次能不能讓渲染管線也一秒只跑 10 次。

這篇是一次可以重做的量測：用程式畫出一棵拆成葉叢的像素樹，讓五種驅動方式共用同一個運動模型，分別是不動（static）、`AnimationController` 每個 vsync 都算（smooth）、`Ticker` 每個 vsync 醒而姿勢 100 ms 才換（tickerStepped）、`Timer` 每 100 ms 算一次（timerStepped）、事件來了才起 `Timer`（eventDriven）；app 用 `addPersistentFrameCallback`、`addTimingsCallback` 與 `CustomPainter.paint` 的計數量每一種方式一秒跑幾次 framework frame、raster frame 與繪製，另外每秒取樣一次行程的 CPU 使用率；接著是兩次實測的結果與量測前預測的對照，以及 tickerStepped 為什麼繪製次數降了、柵格化次數沒有降；完整的 `lib/main.dart` 附在文末。運動模型本身的設計（事件觸發、位置相位、中心穩邊緣鬆）與這個結果在 App 設計上的意義，寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕。

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

渲染管線一次跑下來，可以在 framework、engine 與樹的繪製這幾處計數，各處的次數不一定相同：

```dart
class Stats {
  Stats._();
  static final Stats instance = Stats._();

  int frameworkFrames = 0; // drawFrame 被呼叫的次數
  int rasterFrames = 0; // engine 回報的 FrameTiming 數
  int paints = 0; // 樹的 CustomPainter.paint 次數
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
- **raster frame**：`addTimingsCallback` 收到的每一筆 `FrameTiming` 代表 engine 柵格化並送出了一幀。engine 會批次回報，`SchedulerBinding.addTimingsCallback` 的文件寫的間隔是 profile 與 debug 模式大約 100 ms 一批、release 模式大約 1 秒一批，所以這個數字只拿來算一段時間的總數，不拿來對齊單一幀。`rasterDuration` 與 `buildDuration` 累加起來，除以幀數就是平均每幀的柵格化與 build 時間。
- **paint**：在樹的 `CustomPainter.paint` 第一行把計數加一，數的是樹這一層真正重畫了幾次。

`WidgetsFlutterBinding.ensureInitialized()` 要在 `install()` 之前：`SchedulerBinding.instance` 在 binding 建立之前是 null，少了這一行，app 一啟動就在 `Stats.install` 拋出 `Null check operator used on a null value`。這次第一輪量測就停在這個錯誤上。

`flutter run` 不帶模式旗標時是 debug 模式，服務的是開發中的 hot reload 與斷言檢查；這次要量的是接近出貨版本的幀數，所以改用 profile 模式。debug 模式的 Dart 程式碼跑在 JIT 上，還開著各種斷言，每一幀的時間比實際出貨的版本長，`FrameTiming` 的文件也註明 debug 模式的數字跟 profile、release 模式不同。profile 模式用 AOT 編譯、關掉斷言，同時保留 DevTools 連得上的 timeline；release 模式的 `FrameTiming` 一樣拿得到，但 DevTools 的 timeline 拿掉了，要對照 timeline 時就沒有材料。

## 樹與運動模型

樹由程式產生：48 × 56 格，每格畫成 6 × 6 邏輯點的方塊，下文的「格」都指這個方塊，對應原文（SpriteCook〈[Pixel art trees in the wind](https://www.spritecook.ai/blog/pixel-art-trees-wind-animation)〉）的一個像素。這兩個尺寸是這次取的值，沒有比較其他值；格數只影響每次繪製的方塊數，不影響幀數。樹幹是固定的一組格子；樹冠是一個橢圓，橢圓裡的每一格指派給最近的葉叢中心，共 14 叢；葉叢邊界上的格子畫成深色輪廓。內層是樹冠往內縮一格、用固定深色畫的一層，葉叢位移時從縫裡露出來；原文是往內縮 2 像素、顏色乘 0.55，這次的實作簡化成一格，不影響幀數的量測。

每一叢葉子帶一個權重：0.35 + 0.65 × (葉叢中心到樹冠中心的距離 ÷ 15 格)，上限 1.0，這棵樹的 14 叢的權重在 0.4 到 0.96 之間。15 格是這次取的正規化距離，比外圈葉叢到中心的水平距離 14 格略大，沒有比較其他值；原文只寫了權重從中心的 0.35 線性增加到邊緣的 1.0。位移的公式取自原文：

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

- `t` 是秒數；1.54 秒是一個擺動循環的長度，69 是兩個波峰之間隔幾格（原文寫 69 像素）。
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

`CustomPainter.shouldRepaint` 比較新舊兩組位移，完全相同就回 false：姿勢沒變時，framework 即使跑了一幀也不會重畫這一層。樹包在 `RepaintBoundary` 裡，它重畫時不會連帶重畫畫面上的其他元件。

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

`gust()` 在互動模式下接在樹的 `GestureDetector.onTap` 上；自動量測模式下，另一個 `Timer` 每 5 秒呼叫它一次，模擬一筆資料更新進來。5 秒是這次取的間隔（程式裡的常數 `kEventEverySeconds`，不能從指令列改），沒有比較其他值；間隔拉長時，eventDriven 每秒的平均幀數照比例下降，每一陣風的幀數不變。這個設定下，每 5 秒裡大約 4 秒在動，〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈資料小工具的重繪頻率與資料變化頻率〉說明了這個比例看起來跟一直擺動差不多。5 秒與 4 秒是為了讓 9 秒的計數窗碰到兩次事件、又量得到一整陣風的幀數，不是事件觸發設計的建議值；照那一篇把一陣縮到 1 秒以內時，每一陣約 10 幀，同樣 5 秒一次事件時平均約每秒 2 幀（從 `Timer` 的 100 ms 間隔推論，沒有實跑）。

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

兩次實測的 9 秒平均（每秒的次數，斜線前是第一次、後是第二次；CPU 欄是兩次取樣讀數的範圍）：

| 驅動方式      | framework frame | raster frame  | paint         | CPU 取樣                                  |
| ------------- | --------------- | ------------- | ------------- | ----------------------------------------- |
| static        | 0 / 0           | 0 / 0         | 0 / 0         | 0%                                        |
| smooth        | 144.2 / 139.2   | 145.1 / 139.7 | 144.2 / 139.2 | 多數秒 53% 到 68%（第二次有一秒掉到 30%） |
| tickerStepped | 144.3 / 143.9   | 144.2 / 143.4 | 9.2 / 9.2     | 30% 到 60%                                |
| timerStepped  | 9.8 / 9.8       | 9.8 / 9.8     | 9.8 / 9.8     | 3% 到 6%                                  |
| eventDriven   | 4.4 / 4.4       | 4.4 / 4.4     | 4.4 / 4.4     | 起風時 3% 到 7%，事件之間 0% 到 0.4%      |

五種方式都跟預測一致。第二次 smooth 的平均低一點，是因為 app 在其中一秒只跑了 101 幀，其餘 8 秒都在 143 到 145 之間；CPU 掉到 30% 的那一秒跟這一秒同時。smooth 與 tickerStepped 的 raster frame，逐秒的值在 134 到 152 之間跳動，9 秒的總數跟 framework frame 相差不到一批（第一次 smooth 的 raster 對 framework：1306 對 1298）。從 profile 模式約 100 ms 一批推論，跳動來自一批回報跨過整秒邊界：100 ms 在 144 Hz 下約 14 幀，跟 135 與 150 相差的 15 幀相近。

eventDriven 每秒的 framework frame 長這樣（第一次）：`0 0 6 9 6 3 0 8 8`。九個數字依序是切換到 eventDriven 之後第 3 到第 12 秒之間的每一秒；事件在切換後第 5 秒與第 10 秒觸發，所以第三個數字（第 5 到第 6 秒）開始有幀。每一陣風持續大約 4 秒，陣風包絡本身 2.4 秒，之後是彈簧回彈到停止，共 24 幀左右；兩陣之間是 0。第二陣在計數窗結束時還沒跑完。

## 讀法：tickerStepped 的繪製次數與柵格化次數

tickerStepped 的繪製降到每秒 9.2 次，framework frame 與 raster frame 卻跟 smooth 一樣多。原因在 Flutter 的 `Ticker.scheduleTick()` 與 `RendererBinding.drawFrame()`：

- `Ticker.scheduleTick()` 每一次都呼叫 `SchedulerBinding.instance.scheduleFrame()`，所以一個啟動中的 `Ticker` 每個 vsync 都排一幀，不管它的回呼有沒有呼叫 `setState`。`scheduleFrame()` 在 Flutter 按需重繪裡的角色，寫在〔[Flutter scheduleFrame()：按需 render 的最底層原語](/work-log/flutter_schedule_frame/)〕。
- `RendererBinding.drawFrame()` 每次執行都依序跑 `flushLayout`、`flushCompositingBits`、`flushPaint`，再對每個 `RenderView` 呼叫 `compositeFrame()`，把圖層樹送給 engine 柵格化。沒有任何 render object 被標成 dirty 時，前三步幾乎不做事，`compositeFrame()` 仍然送出一幀。〔[Flutter 畫面落後邏輯狀態（log 正確、畫面不符）— 重繪訊號排查與心跳做法](/work-log/flutter_repaint_heartbeat/)〕的重繪心跳依賴的是同一個性質：定時排一幀，畫面就會重新合成。

所以在 tickerStepped 裡，樹這一層一秒只重畫 9 次，整個畫面的合成與柵格化仍然一秒 144 次。兩次實測的平均每幀柵格化時間（`RESULT` 行的 `avgRaster`，來自 `FrameTiming.rasterDuration`）在 tickerStepped 是 2.25 與 2.56 ms，在 smooth 是 2.27 與 2.15 ms；另一次照本篇重做的縮短版量測是 2.09 對 1.57 ms，兩者的大小關係不固定，這幾次的量測分不出差別。CPU 取樣的範圍也互相重疊（smooth 多數秒 53% 到 68%，tickerStepped 30% 到 60%），所以在這個場景裡，只減少繪製次數，CPU 的差別落在取樣的雜訊範圍內。這棵樹每次繪製只有幾百個方塊，繪製本身很便宜；繪製成本高的插圖（大量 path、模糊、shader），減少繪製省下的時間會比這裡多，這次沒有量。兩者的差別在 smooth 每個 vsync 都多做一次姿勢計算、`setState` 的 rebuild 與繪製，tickerStepped 的 `Ticker` 回呼每個 vsync 也會執行一次，只是不到 100 ms 就直接返回。

把驅動器換成 `Timer`（timerStepped）之後，沒有任何驅動器在每個 vsync 排幀，三個計數一起降到每秒 10 次左右，CPU 降了一個數量級。事件觸發的版本再把事件之間的那幾秒也降到 0。這個結果對照遊戲引擎與按需重繪的 UI 框架的差別，寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈重繪成本與動畫驅動器的排幀頻率〉。

## 未量測的範圍：手機耗電、60 Hz 螢幕、合成器動畫、執行緒拆分

- **手機的耗電**：這次只量了桌面的幀數與 CPU 取樣。手機上要用 Xcode Instruments 的 Energy Log 或 Android Studio 的 Power Profiler 量，這次在桌面上量不到 GPU 與螢幕的耗電。
- **60 Hz 螢幕上的差距**：smooth 與 tickerStepped 的幀數會降到每秒 60 次左右，timerStepped 與 eventDriven 不受螢幕更新率影響，所以前兩種與 timerStepped 的幀數比會從 144 ÷ 9.8 ≈ 14 倍縮小到 60 ÷ 9.8 ≈ 6 倍（從機制推論，這次沒有在 60 Hz 螢幕上跑）。
- **合成器動畫**：Flutter 的動畫由 framework 在 Dart 端每幀驅動，沒有交給平台合成器的路徑，所以這次沒有對照 CSS `transform` 動畫或 Core Animation 的版本。
- **減少動態的設定**：這個 demo 沒有讀減少動態的設定；實際的 App 在 `MediaQuery.disableAnimationsOf(context)` 為 true 時，不起陣風，或只換顏色（〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈減少動態的系統設定與 WCAG 2.2.2〉）。
- **macOS 的 merged thread**：這次的 Flutter 在 macOS 上預設把 UI 執行緒與平台執行緒合併（啟動 log 印出 `Running with merged UI and platform thread. Experimental.`），`ps` 量到的是整個行程的 CPU，沒有分執行緒。

## 附錄：完整的 `lib/main.dart`

整份取代 `flutter create` 產生的 `lib/main.dart`。互動模式（`flutter run -d macos`）用畫面下方的 chip 切換驅動方式，eventDriven 時點樹起一陣風；自動量測照〈自動量測與 CPU 取樣〉的指令跑。

```dart
// 像素樹風吹動畫：五種驅動方式的重繪成本比較。
//
// 每一種驅動方式畫同一棵樹、用同一個運動模型（位置決定相位的行進波、
// 中心穩邊緣鬆、整數像素位移），差別只在「誰叫 Flutter 排 frame、多常排」：
//
//   static         不動，基準線
//   smooth         AnimationController 每個 vsync 算一次、位移不取整
//   tickerStepped  Ticker 每個 vsync 跑，姿勢 100ms 才變一次（原文的驅動結構，省掉彈簧）
//   timerStepped   Timer 每 100ms 算一次姿勢，有變才 setState
//   eventDriven    平常靜止；事件（點擊或模擬的資料更新）來了才起一陣風，
//                  風停、樹回正之後 Timer 自己取消
//
// 自動量測：flutter run --profile -d macos --dart-define=AUTO=true
// 每種方式跑 MODE_SECONDS 秒，丟掉前 WARMUP_SECONDS 秒，印出每秒的
// framework frame 數、raster frame 數（FrameTiming）、paint 次數，跑完 exit(0)。
import 'dart:async';
import 'dart:io' show exit;
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

const bool kAuto = bool.fromEnvironment('AUTO');
const int kModeSeconds = int.fromEnvironment('MODE_SECONDS', defaultValue: 12);
const int kWarmupSeconds = int.fromEnvironment('WARMUP_SECONDS', defaultValue: 3);

/// 事件驅動模式在自動量測時，每隔幾秒模擬一次資料更新。
const int kEventEverySeconds = 5;

/// 姿勢的更新間隔（原文 POSE_TIME := 0.1）。
const Duration kPoseInterval = Duration(milliseconds: 100);

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
  int paints = 0; // 樹的 CustomPainter.paint 次數
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
// 樹的資料：程式產生的像素樹，拆成樹幹、內層與一叢一叢的葉子
// ---------------------------------------------------------------------------

class Cell {
  const Cell(this.x, this.y, this.color);
  final int x;
  final int y;
  final Color color;
}

class Clump {
  Clump(this.cells, this.cx, this.cy, this.weight);
  final List<Cell> cells;
  final double cx; // 葉叢中心（樹的像素座標）
  final double cy;
  final double weight; // 0.35 + 0.65 × (到樹冠中心的距離 ÷ 15)，上限 1.0
}

class Tree {
  Tree._(this.trunk, this.inside, this.clumps);
  final List<Cell> trunk;
  final List<Cell> inside;
  final List<Clump> clumps;

  static const int width = 48;
  static const int height = 56;

  static Tree build() {
    final rnd = math.Random(7);
    final trunk = <Cell>[];
    const bark = Color(0xFF6B4423);
    const barkDark = Color(0xFF4A2E17);
    for (var y = 30; y < height; y++) {
      final half = y > 50 ? 3 : 2;
      for (var x = 24 - half; x <= 24 + half; x++) {
        trunk.add(Cell(x, y, x == 24 - half ? barkDark : bark));
      }
    }

    // 葉叢中心：圍著樹冠中心 (24, 20) 排一圈加中間幾叢。
    final centers = <math.Point<double>>[
      const math.Point(24, 18),
      const math.Point(19, 22),
      const math.Point(29, 22),
    ];
    for (var i = 0; i < 11; i++) {
      final a = i / 11 * 2 * math.pi;
      centers.add(math.Point(24 + math.cos(a) * 14, 19 + math.sin(a) * 11));
    }

    final owner = <int, int>{}; // cell key -> clump index（最近的中心）
    final shape = <int>{};
    for (var y = 0; y < 38; y++) {
      for (var x = 0; x < width; x++) {
        final dx = (x - 24) / 21;
        final dy = (y - 19) / 17;
        if (dx * dx + dy * dy <= 1 + (rnd.nextDouble() - 0.5) * 0.15) {
          shape.add(y * width + x);
        }
      }
    }
    for (final key in shape) {
      final x = key % width, y = key ~/ width;
      var best = 0;
      var bestD = double.infinity;
      for (var i = 0; i < centers.length; i++) {
        final d = math.pow(x - centers[i].x, 2) + math.pow(y - centers[i].y, 2);
        if (d < bestD) {
          bestD = d.toDouble();
          best = i;
        }
      }
      owner[key] = best;
    }

    const leafLight = Color(0xFF7FBF4D);
    const leaf = Color(0xFF4E9A3A);
    const leafDark = Color(0xFF2F6B2A);
    const outline = Color(0xFF1E3F1F);
    final clumps = <Clump>[];
    for (var i = 0; i < centers.length; i++) {
      final cells = <Cell>[];
      for (final e in owner.entries.where((e) => e.value == i)) {
        final x = e.key % width, y = e.key ~/ width;
        bool sameOwner(int nx, int ny) => owner[ny * width + nx] == i;
        final edge = !sameOwner(x - 1, y) || !sameOwner(x + 1, y) || !sameOwner(x, y - 1) || !sameOwner(x, y + 1);
        final rel = (y - centers[i].y);
        final color = edge ? outline : (rel < -2 ? leafLight : (rel > 2 ? leafDark : leaf));
        cells.add(Cell(x, y, color));
      }
      final c = centers[i];
      final dist = math.min(1.0, math.sqrt(math.pow(c.x - 24, 2) + math.pow(c.y - 19, 2)) / 15);
      clumps.add(Clump(cells, c.x, c.y, 0.35 + (1 - 0.35) * dist));
    }

    // 內層：整個樹冠往內縮一格、用固定的深色（原文是內縮 2 像素、顏色乘 0.55），
    // 填葉叢移開時露出的縫。
    final inside = <Cell>[];
    for (final key in shape) {
      final x = key % width, y = key ~/ width;
      final inner = shape.contains(key - 1) && shape.contains(key + 1) && shape.contains(key - width) && shape.contains(key + width);
      if (inner) inside.add(Cell(x, y, const Color(0xFF1A3A17)));
    }
    return Tree._(trunk, inside, clumps);
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

/// 算出每一叢葉子的位移。[quantize] 為 true 時取整數像素。
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
// 畫樹
// ---------------------------------------------------------------------------

class TreePainter extends CustomPainter {
  TreePainter(this.tree, this.pose);
  final Tree tree;
  final List<Offset> pose;

  @override
  void paint(Canvas canvas, Size size) {
    Stats.instance.paints++;
    final px = size.width / Tree.width;
    final paint = Paint()..isAntiAlias = false;
    void cell(Cell c, Offset o) {
      paint.color = c.color;
      canvas.drawRect(Rect.fromLTWH((c.x + o.dx) * px, (c.y + o.dy) * px, px, px), paint);
    }

    for (final c in tree.trunk) {
      cell(c, Offset.zero);
    }
    for (final c in tree.inside) {
      cell(c, Offset.zero);
    }
    for (var i = 0; i < tree.clumps.length; i++) {
      for (final c in tree.clumps[i].cells) {
        cell(c, pose[i]);
      }
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
          size: const Size(Tree.width * 6.0, Tree.height * 6.0),
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
      home: Scaffold(
        backgroundColor: const Color(0xFFE8F0E0),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SwayTree(key: ValueKey(mode), mode: mode, tree: tree),
              const SizedBox(height: 16),
              Text(kAuto ? '自動量測：${mode.name}' : '模式：${mode.name}（eventDriven 時點樹起風）'),
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
