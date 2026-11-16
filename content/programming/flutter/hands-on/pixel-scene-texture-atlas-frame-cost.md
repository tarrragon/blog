---
title: "Flutter 像素場景的每幀柵格化成本：紋理圖集、背景點陣圖、獨立圖層與不 rebuild 的改法與量測"
date: 2026-11-17
description: "Flutter 畫面上有幾十個各自位移的小圖塊、每幀柵格化時間偏長，想知道改用 drawRawAtlas 畫紋理圖集、背景改成點陣圖、換姿勢不 rebuild 這幾處合起來能省下多少每幀時間時讀：從驅動方式比較的量測 app 改起的程式、改前改後的畫面比對，以及 144 Hz 螢幕上的每幀柵格化、build 與 CPU 取樣。"
weight: 2
tags: ["flutter", "rendering", "performance", "hands-on"]
---

2026-11-17 在一台 macOS 15（Darwin 24.3）的 Mac 上做的量測：Flutter 3.41.3（Dart 3.11.1），以 profile 模式跑 macOS 桌面版，app 視窗開在一台更新率 144 Hz 的外接螢幕上。渲染後端是 Skia：這一版 Flutter 的 macOS 桌面版在 App 的 `Info.plist` 沒有 `FLTEnableImpeller` 時不開 Impeller（engine 原始碼 `shell/platform/darwin/macos/framework/Source/FlutterDartProject.mm` 的 `enableImpeller`），這次的專案沒有設這個鍵，`flutter run` 也沒有帶開 Impeller 的參數；log 沒有印出後端的名字，所以這是從原始碼與設定推得的。當時拿〔[Flutter 裝飾性動畫的驅動方式比較](/programming/flutter/hands-on/ambient-motion-frame-cost/)〕的量測 app（橡樹與松樹的像素場景、五種驅動方式、自動量測），把場景的繪製方式改掉；改之前先用那一篇附錄的程式跑一次自動量測，改之後跑兩次。

這篇整理那一次改繪製方式的做法與量測：量測 app 原本每一幀要柵格化（把繪圖指令轉成螢幕上的像素）多少個矩形、時間花在 build 還是柵格化；把葉叢拼成一張紋理圖集（texture atlas）用 `drawRawAtlas` 一次畫完、背景改成一張點陣圖並放進自己的 `RepaintBoundary`、姿勢經由 `ValueNotifier` 觸發重畫而不 rebuild，這幾處程式怎麼改；改完怎麼在 `flutter test` 裡逐位元組比對，確認畫面跟原本相同；以及五種驅動方式的每幀柵格化、每幀 build 與 CPU 取樣跟改之前比各降了多少、哪些沒有降。量測 app 本身（場景與運動模型、五種驅動方式、計數器、自動量測與 CPU 取樣的指令）與驅動方式怎麼決定一秒排幾幀，寫在〔[Flutter 裝飾性動畫的驅動方式比較](/programming/flutter/hands-on/ambient-motion-frame-cost/)〕；這篇的程式是在那一篇附錄的 `lib/main.dart` 上改幾段。這個改法在什麼條件下省得到時間（內容能不能事先畫好、圖塊多少、紋理尺寸上限、取樣方式、渲染後端），寫在 [Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/) 卡。驅動方式與每幀成本在 App 設計上的意義（裝飾性動畫該用哪一種驅動器、事件觸發的成本），寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈重繪成本與動畫驅動器的排幀頻率〉。

下文的兩個版本：**基準**是驅動方式比較那一篇附錄的程式，**改過的版本**是這篇改完的程式。

## 量測 app 原本每一幀的繪圖指令數，以及 build 與柵格化的時間

渲染管線每跑一次，花的時間分在兩條執行緒上：UI 執行緒跑 build（rebuild、layout、繪製，把繪圖指令錄成圖層樹），raster 執行緒把圖層樹柵格化（[Flutter Thread Model](/programming/flutter/knowledge-cards/flutter-thread-model/)）。驅動方式比較那一篇改的是渲染管線一秒跑幾次；這篇改繪製方式，要縮短的是每跑一次所花的時間。

那一篇的場景是 168 × 100 格的像素畫，每一格在畫面上是 4 × 4 邏輯點的方塊，下文的「格」都指這個方塊。場景裡的橡樹有 32 叢葉子、松樹有 9 層枝層，程式把每一叢、每一層各錄成一張 [Picture](/programming/flutter/knowledge-cards/picture/)，下文的「葉叢」包含松樹的枝層，共 41 叢；樹幹、樹冠內層與草另外錄成一張背景的 `Picture`。這些 `Picture` 裡錄的是一格一個 1 × 1 的 `drawRect`：附錄的程式用一個小函式 `_Pen.px` 畫每一格（`Paint` 設 `isAntiAlias = false`，邊緣不反鋸齒），這次在 `_Pen.px` 裡加一個計數器（只放在暫時的測試檔，不改 app），跑一次 `Tree.build()`，背景加葉叢共呼叫 11,046 次。

每一幀，附錄的 `TreePainter` 重播背景與 41 叢的 `Picture`。重播省下的是 UI 執行緒重新計算每一格顏色的時間；raster 執行緒每一幀仍然要把這 11,046 個矩形柵格化一次（[Picture](/programming/flutter/knowledge-cards/picture/) 卡的〈跟其他概念的關係〉）。那一篇 2026-11-16 的量測裡，每個 vsync 都重畫的 smooth 每幀 build 是 0.38 ms，柵格化是 3.7 ms，柵格化佔了大部分。3.7 ms 沒有超過 144 Hz 的幀預算（約 6.9 ms），那一篇量到的 framework frame 與 raster frame 也都是每秒約 144 次，所以這次要省的是 CPU 的用量，不是掉幀。改的方向是減少 raster 執行緒每一幀的工作；驅動方式、運動模型、畫面大小與計數的程式都跟附錄相同，不同的只有繪製方式：

- **葉叢拼成紋理圖集，每一幀用一次 `drawRawAtlas` 畫完**：raster 執行緒每一幀不再逐格柵格化葉叢的矩形。
- **背景畫成一張點陣圖**：背景的 `Picture` 在啟動時柵格化一次，之後每一幀只畫一次 `drawImage`，raster 執行緒每一幀不再柵格化背景的矩形。
- **背景放進自己的 `RepaintBoundary`**：葉叢換姿勢時，背景那一層的圖層直接沿用，UI 執行緒不重錄背景。
- **姿勢經由 `ValueNotifier` 觸發重畫**：換姿勢時不呼叫 `setState`，省掉 rebuild。

這幾處改動是一起量的，下文的降幅是它們合起來的結果。讀者的機器量到的數字跟那一篇不一定相同，所以動手改之前，先用附錄的程式照那一篇〈自動量測與 CPU 取樣〉跑一次，存下 log 與 CPU 取樣當基準。改完之後才想到要補基準時，先把程式還原成附錄的版本再跑。

## 葉叢拼成紋理圖集：`Atlas.pack` 與 `drawRawAtlas`

紋理圖集（texture atlas）是把很多張小圖排進同一張大圖、記下每一張在大圖裡佔的矩形，畫的時候依矩形取出來（[Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/)）。這個場景的每一叢葉子只會平移、內容不變，所以程式在啟動時把每一叢柵格化一次、拼進圖集，之後每一幀從圖集取出每一叢、貼到它這一刻的位置。這裡有兩件事：啟動時先把每一叢畫成點陣圖，raster 執行緒每一幀不必重新柵格化那些矩形；拼成一張圖，41 次繪圖呼叫合成一次。`dart:ui` 的 `Canvas.drawAtlas` 文件寫明，從一張圖畫出很多塊時，它比逐塊呼叫 `drawImageRect` 有效率；`drawRawAtlas` 是同一個方法改用型別陣列（變換與來源矩形用 `Float32List`、顏色用 `Int32List`）傳參數的版本，文件寫它又比 `drawAtlas` 有效率，因為參數已經是繪製程式直接能用的格式。這次用 `drawRawAtlas`，沒有實跑 `drawAtlas` 或逐叢 `drawImageRect` 的版本比較，所以預先柵格化與拼成圖集各省了多少，這次分不出來。三者用同一張圖、同樣的取樣方式時畫出的結果相同（推論，沒有實跑）。

`Float32List` 在 `dart:typed_data` 裡，`lib/main.dart` 開頭先加一行 import（`package:flutter/material.dart` 沒有匯出它）：

```dart
import 'dart:typed_data';
```

程式要記下每一叢在場景裡佔哪一塊，所以 `Clump` 多一個 `bounds`，在建構時從那一叢的格子集合算出。整個 `Clump` 類別換成下面這一份，附錄裡兩處 `clumps.add(Clump(...))` 都在第二個引數的位置多傳那一叢的格子集合 `cells`（橡樹與松樹那兩段程式裡，這個集合的變數都叫 `cells`）：

```dart
class Clump {
  Clump(this.picture, Set<int> cells, this.cx, this.cy, this.weight) : bounds = _boundsOf(cells);
  final ui.Picture picture; // 這一叢的像素，座標單位是格（場景座標）
  final Rect bounds; // 這一叢佔的格子範圍（場景座標，含右下邊界）
  final double cx; // 葉叢中心（格）
  final double cy;
  final double weight; // 中心或下層小、邊緣或上層大，0.35 到 1.0

  static Rect _boundsOf(Set<int> cells) {
    var x0 = Tree.width, y0 = Tree.height, x1 = 0, y1 = 0;
    for (final k in cells) {
      final x = k % Tree.width, y = k ~/ Tree.width; // 格子用 y * width + x 編號
      x0 = math.min(x0, x);
      y0 = math.min(y0, y);
      x1 = math.max(x1, x + 1);
      y1 = math.max(y1, y + 1);
    }
    return Rect.fromLTRB(x0.toDouble(), y0.toDouble(), x1.toDouble(), y1.toDouble());
  }
}
```

啟動時把全部葉叢拼成一張圖，`Atlas` 是新增的類別：

```dart
class Atlas {
  Atlas._(this.image, this.rects);
  final ui.Image image;
  final Float32List rects; // 每叢四個值：left, top, right, bottom（atlas 座標）

  static Atlas pack(List<Clump> clumps) {
    const maxWidth = 256, gap = 1;
    final rects = Float32List(clumps.length * 4);
    var x = gap, y = gap, rowHeight = 0, usedWidth = 0;
    final rec = ui.PictureRecorder();
    final canvas = Canvas(rec);
    for (var i = 0; i < clumps.length; i++) {
      final b = clumps[i].bounds;
      final w = b.width.toInt(), h = b.height.toInt();
      if (x + w + gap > maxWidth) { // 這一排擺不下，換下一排
        x = gap;
        y += rowHeight + gap;
        rowHeight = 0;
      }
      canvas.save();
      canvas.translate(x - b.left, y - b.top); // 把這一叢從場景座標搬到圖集裡的位置
      canvas.drawPicture(clumps[i].picture);
      canvas.restore();
      rects.setAll(i * 4, [x.toDouble(), y.toDouble(), (x + w).toDouble(), (y + h).toDouble()]);
      x += w + gap;
      usedWidth = math.max(usedWidth, x);
      rowHeight = math.max(rowHeight, h);
    }
    final image = rec.endRecording().toImageSync(usedWidth, y + rowHeight + gap);
    return Atlas._(image, rects);
  }
}
```

- 每一叢的 `Picture` 座標單位是格，所以 `toImageSync` 柵格化出來的圖是 1 格 = 1 px；這次 41 叢拼成的圖集是 253 × 59 px（跟數 `_Pen.px` 呼叫次數的那個暫時測試檔一起印出）。畫到畫面上時，painter 的 `paint` 先呼叫 `canvas.scale` 把座標放大 4 倍。
- `toImageSync` 在呼叫的當下回傳 `ui.Image`，engine 在背後把圖柵格化好；另一個方法 `toImage` 回傳 `Future`，用它的話 `Tree` 的建構要改成非同步、等它完成。這次選 `toImageSync`，讓 `Tree.build()` 維持同步、`DemoApp` 建立 `Tree` 時不必等待；沒有比較兩者啟動時的耗時。
- `gap` 是叢與叢之間的 1 px 透明空隙。取樣方式會混合相鄰像素時（`FilterQuality.low` 以上），畫到矩形邊緣可能混進隔壁那一叢的顏色，留空隙讓混進來的是透明（從取樣的機制推論）。這次用最近鄰取樣，它只取最接近的那一個來源像素，在邊緣不反鋸齒時取到的都在矩形內，smooth 的位移不是整數格時也一樣，所以這個場景不留空隙大概也畫得對（推論，沒有實跑；`_pixelPaint` 沒有關掉反鋸齒，Skia 怎麼對 `drawAtlas` 套用反鋸齒這次沒有查到）；留著 1 px 是為了改用其他取樣方式時不必重排圖集。1 px 是這次取的值，沒有跟不留空隙或更寬的空隙比較過。
- `maxWidth` 256 是這次取的一排寬度，沒有比較其他值；在一排的最小寬度與紋理尺寸上限之內，改大改小只改變圖集的長寬比。一排至少要放得下最寬的那一叢加兩邊的 `gap`，否則那一叢會超出這一排；整張圖集的長與寬不能超過 GPU 允許的最大 2D 紋理尺寸，`dart:ui` 文件寫超過時要等畫這張圖的那一刻才丟出 `PictureRasterizationException`（這次的 253 × 59 px 沒有碰到這個限制，各裝置的上限這次沒有查）。
- 背景的 `Picture` 也在啟動時用 `toImageSync(168, 100)` 畫成一張圖。兩張圖都在 `Tree` 的建構子裡產生，`Tree._` 與它的欄位換成：

```dart
Tree._(this.back, this.clumps)
    : backImage = back.toImageSync(width, height),
      atlas = Atlas.pack(clumps);
final ui.Picture back; // 不會動的部分
final List<Clump> clumps; // 依繪製順序排列（後面的蓋在前面的上面）
final ui.Image backImage; // back 畫成的圖，1 格 = 1 px
final Atlas atlas; // clumps 拼成的圖
```

這個場景的每一格都是一個同色方塊，所以 1 格 = 1 px 的圖放大 4 倍、每一格變成 4 × 4 的同色方塊時，跟逐格畫 4 × 4 的方塊是同一個結果。這個等式有幾個前提：附錄逐格畫方塊時不反鋸齒；放大倍數是整數，格子的邊界落在整數像素上；取樣方式是最近鄰取樣（nearest-neighbor：每個畫面像素的顏色直接等於最接近的那一個來源像素的顏色）。〈兩種畫法的畫面比對〉在這幾個前提下確認了取整位移時像素相同。裝置的像素比不是整數時（每一格的實體像素數是小數），兩種畫法的邊緣可能不同，這次沒有比對。向量風格的內容柵格化之後再放大會失真，要照畫面上的顯示尺寸與裝置的像素比柵格化，代價是圖片的記憶體照面積增加（推論，這次的場景不需要）。

附錄的 `TreePainter` 換成兩個 painter，背景一個、葉叢一個：

```dart
final Paint _pixelPaint = Paint()..filterQuality = FilterQuality.none;

class BackPainter extends CustomPainter {
  BackPainter(this.tree);
  final Tree tree;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.width / Tree.width);
    canvas.drawImage(tree.backImage, Offset.zero, _pixelPaint);
  }

  @override
  bool shouldRepaint(BackPainter old) => old.tree != tree;
}

class LeavesPainter extends CustomPainter {
  LeavesPainter(this.tree, this.pose)
      : transforms = Float32List(tree.clumps.length * 4),
        super(repaint: pose);
  final Tree tree;
  final ValueListenable<List<Offset>> pose;
  final Float32List transforms; // 每叢四個值：scos, ssin, tx, ty（RSTransform）

  @override
  void paint(Canvas canvas, Size size) {
    Stats.instance.paints++;
    canvas.scale(size.width / Tree.width);
    final p = pose.value;
    for (var i = 0; i < tree.clumps.length; i++) {
      final b = tree.clumps[i].bounds;
      transforms
        ..[i * 4] = 1 // scos：縮放 1、不旋轉
        ..[i * 4 + 1] = 0 // ssin
        ..[i * 4 + 2] = b.left + p[i].dx // 這一叢在場景裡的位置加上位移
        ..[i * 4 + 3] = b.top + p[i].dy;
    }
    canvas.drawRawAtlas(tree.atlas.image, transforms, tree.atlas.rects, null, null, null, _pixelPaint);
  }

  @override
  bool shouldRepaint(LeavesPainter old) => old.tree != tree || old.pose != pose;
}
```

`ValueListenable` 在 `package:flutter/foundation.dart` 裡，`material.dart` 沒有匯出它；只加上面的程式碼時，`flutter analyze` 報 `Undefined class 'ValueListenable'`，`lib/main.dart` 開頭再加一行：

```dart
import 'package:flutter/foundation.dart' show ValueListenable;
```

`drawRawAtlas` 的引數依序是：

- 圖集與每一塊的變換：`RSTransform` 的四個值是縮放乘上旋轉角的餘弦與正弦，以及平移；只平移時填 1、0。
- 每一塊的來源矩形：`Atlas.pack` 記下的 `rects`。
- 每一塊要混合的顏色與混合模式：給 `null`，代表不混色。
- 裁切的估計範圍（`cullRect`）：文件寫它讓 engine 拿這個範圍跟裁切區比對，整批都在畫面外時直接跳過；給 `null` 代表不提供，這個場景的葉叢全在畫面內，提供了也不會跳過。
- 畫圖用的 `Paint`。

`Paint.filterQuality` 控制放大與縮小點陣圖時的取樣方式，`dart:ui` 的文件把它寫成效能與品質之間的取捨，預設值是 `FilterQuality.none`，也就是最近鄰取樣，取捨裡最快的那一端。程式碼明寫這個值只是讓用意看得到，跟預設值相同。文件寫 `FilterQuality.low` 用雙線性內插，改成 `low` 以上時，取樣會在相鄰的格子之間混色，格子的邊緣變糊（這次沒有實跑）。

paint 的次數照驅動方式比較那一篇的計數，數的是場景那一層重畫的次數：`LeavesPainter` 把計數放在 `paint` 第一行，跟附錄的 `TreePainter` 一樣，所以 paint 次數仍然是葉叢那一層重畫的次數；背景的 `BackPainter` 不計數，它只在切換驅動方式、整個場景重建時畫一次。

## 背景獨立圖層與換姿勢不 rebuild：`RepaintBoundary` 與 `ValueNotifier`

Flutter 的畫面分成兩層物件：widget 描述畫面該長什麼樣，每次 rebuild 都重新建一份；render object 是實際做 layout 與繪製的那一層，在 rebuild 之間保留下來（兩層之間還有保留 `State` 的 element；三者的分工，以及 rebuild、layout、paint 各自怎麼被標記，見 [Widget、Element 與 RenderObject（Flutter 的三棵樹）](/programming/flutter/knowledge-cards/widget-element-renderobject/)）。附錄的 `SwayTreeState` 把姿勢存在一個 `List<Offset>` 欄位，每次換姿勢呼叫 `setState`：framework 把這個 widget 標成要 rebuild，下一幀重建 `GestureDetector`、`RepaintBoundary`、`CustomPaint` 與一個新的 `TreePainter`，`shouldRepaint` 比較新舊兩組位移之後才決定要不要重畫。姿勢改成放在 `ValueNotifier` 裡、交給 `CustomPainter` 建構子的 `repaint` 參數之後，`ValueNotifier` 的值一改，framework 直接把 `CustomPaint` 底下的 render object 標成要重畫，跳過 rebuild。`CustomPainter` 的文件寫的是同時跳過 build 與 layout，不過這個場景省下的只有 rebuild：附錄那一版 rebuild 之後，`CustomPaint` 的大小沒變，framework 換上新的 painter 時本來就只把 render object 標成要重畫，不重新 layout。

```dart
// SwayTreeState 的欄位：取代附錄的 `late List<Offset> pose = ...` 那一行。
// 姿勢改變時只通知葉叢的 CustomPaint 重畫，不呼叫 setState。
late final ValueNotifier<List<Offset>> pose =
    ValueNotifier(List.filled(widget.tree.clumps.length, Offset.zero));

// tickerStepped、timerStepped 與 eventDriven 裡原本的
// if (!samePose(next, pose)) setState(() => pose = next);
// 整行換成：
if (!samePose(next, pose.value)) pose.value = next;
// smooth 的 listener 改成：
// ..addListener(() => pose.value = computePose(widget.tree, t, kBreeze, 0, 0, quantize: false))

// dispose() 裡加一行 pose.dispose();

@override
Widget build(BuildContext context) {
  const size = Size(Tree.width * Tree.cell, Tree.height * Tree.cell);
  return GestureDetector(
    onTap: gust,
    child: RepaintBoundary(
      child: Stack(
        children: [
          RepaintBoundary(child: CustomPaint(size: size, painter: BackPainter(widget.tree))),
          CustomPaint(size: size, painter: LeavesPainter(widget.tree, pose)),
        ],
      ),
    ),
  );
}
```

- `ValueNotifier` 只在新值跟舊值不相等時通知，而 `List` 的 `==` 比較的是兩者是不是同一個物件，所以每次指定新的 `List` 都會通知。smooth 每個 vsync 都算出新的位移，每次都要重畫，直接指定；tickerStepped、timerStepped 與 eventDriven 在指定之前先用 `samePose` 比較，姿勢沒變時不指定，葉叢那一層就不重畫。
- 外層的 `RepaintBoundary` 跟附錄一樣，把整棵樹跟畫面上的文字與切換驅動方式的按鈕隔開；內層的 `RepaintBoundary` 包住背景，葉叢那一層重畫時，背景的圖層沿用上一次錄好的那一份（[RepaintBoundary](/programming/flutter/knowledge-cards/repaint-boundary/)）。
- 背景與葉叢也可以畫在同一個 `CustomPaint` 上，背景用 `painter`、葉叢用 `foregroundPainter`。兩個 painter 這時屬於同一個 render object，葉叢重畫時背景跟著重畫（從機制推論，沒有實跑）；背景已經是一張點陣圖，多畫一次的成本是一次 `drawImage`。這次用 `Stack` 加兩個 `CustomPaint`，讓背景能放進自己的 `RepaintBoundary`。

改完之後在專案資料夾跑 `flutter analyze`，看到 `No issues found!` 再往下做。

## 兩種畫法的畫面比對：在 `flutter test` 裡逐位元組比較同一個姿勢的輸出

繪製方式換了，量到的時間要跟原本比，前提是兩種畫法畫出同一個畫面。這次在 `flutter test` 裡把同一個姿勢用兩種畫法各畫成一張 672 × 400 的圖，比對每一個位元組：一種是基準的畫法（重播背景與每一叢的 `Picture`；`TreePainter` 換掉之後，在測試裡另外寫一份），一種是改過的版本的畫法（背景圖加 `drawRawAtlas`）。測試檔存成 `test/atlas_compare_test.dart`，檔名要以 `_test.dart` 結尾，`flutter test` 才會把它當成測試執行：

```dart
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wind_sway_demo/main.dart';

const Size _size = Size(Tree.width * Tree.cell, Tree.height * Tree.cell);

// 改過之後的畫法。兩個 painter 畫在同一張 Canvas 上，每一個前後 save 與 restore。
void _paintAtlas(Canvas canvas, Tree tree, List<Offset> pose) {
  canvas.save();
  BackPainter(tree).paint(canvas, _size);
  canvas.restore();
  canvas.save();
  LeavesPainter(tree, ValueNotifier(pose)).paint(canvas, _size);
  canvas.restore();
}

// 附錄的畫法：背景與每一叢都重播 Picture。
void _paintPictures(Canvas canvas, Tree tree, List<Offset> pose) {
  canvas.scale(Tree.cell);
  canvas.drawPicture(tree.back);
  for (var i = 0; i < tree.clumps.length; i++) {
    canvas.save();
    canvas.translate(pose[i].dx, pose[i].dy);
    canvas.drawPicture(tree.clumps[i].picture);
    canvas.restore();
  }
}

Future<Uint8List> _render(void Function(Canvas) paint) async {
  final rec = ui.PictureRecorder();
  final canvas = Canvas(rec);
  canvas.drawRect(Offset.zero & _size, Paint()..color = kBackground);
  paint(canvas);
  final image = await rec.endRecording().toImage(_size.width.toInt(), _size.height.toInt());
  return (await image.toByteData(format: ui.ImageByteFormat.rawRgba))!.buffer.asUint8List();
}

void main() {
  testWidgets('atlas 與逐叢 Picture 的像素相同', (tester) async {
    await tester.runAsync(() async {
      final tree = Tree.build();
      for (final pose in [
        List.filled(tree.clumps.length, Offset.zero), // 靜止
        computePose(tree, 0.6, 0, 1, 2.2, quantize: true), // 陣風最強、取整
      ]) {
        final a = await _render((c) => _paintAtlas(c, tree, pose));
        final b = await _render((c) => _paintPictures(c, tree, pose));
        var diff = 0;
        for (var i = 0; i < a.length; i++) {
          if (a[i] != b[i]) diff++;
        }
        expect(diff, 0, reason: '有 $diff 個位元組不同');
      }
    });
  });
}
```

```bash
flutter test test/atlas_compare_test.dart
```

兩個姿勢的兩張圖都相同時，最後一行印出 `All tests passed!`；有位元組不同時，印出 `有 N 個位元組不同` 與 `Some tests failed.`。

- `Tree.cell` 是附錄裡每一格畫成幾個邏輯點的常數（4），`_size` 與 `_paintPictures` 的放大倍數都取它，場景換了格子大小時跟著變。
- `computePose` 的引數依序是時間 `t`、`breeze`、`gust`、`lean`，意義在驅動方式比較那一篇的〈場景與運動模型〉。這裡 `gust` 填 1，是陣風包絡的最高點；`lean` 填 2.2，是彈簧在 `gust` 為 1 時的平衡位置（推力 2.2 乘上 1），也就是樹身最傾斜的時候；`breeze` 填 0，照事件觸發的設定不加持續的微風；`t` 填 0.6 秒，是任取的一個相位，沒有比較其他值。
- `toImage` 是非同步的柵格化，這次照 Flutter 測試裡執行真正非同步工作的寫法，把整段包在 `tester.runAsync` 裡，沒有試過不包的寫法。

這次兩個姿勢的兩張圖都完全相同。這個比對是在 `flutter test` 裡做的，`flutter test` 的執行環境沒有 GPU（推論，這次沒有查證）。`dart:ui` 文件寫 `toImageSync` 在沒有 GPU 的環境改用 CPU 柵格化，這涵蓋圖集與背景圖；比對的兩張圖由 `toImage` 產生，它的文件沒有寫用 CPU 還是 GPU，在測試裡同樣走 CPU 是推論。所以比對的是 CPU 柵格化的結果（推論）；macOS app 視窗裡用 GPU 畫出的畫面，沒有逐像素比對過。

這個比對第一次跑時報出 388,320 個位元組不同：當時 `_paintAtlas` 沒有 `save()` 與 `restore()`，`BackPainter` 呼叫的 `canvas.scale(4)` 留在 Canvas 上，`LeavesPainter` 在同一張 Canvas 上再放大一次，葉叢被放大成 16 倍。app 裡兩個 painter 各自有一張 `Canvas`，不會這樣；測試裡補上 `save()` 與 `restore()` 之後比對通過。這次失敗也顯示兩張圖不同時這個比對會報錯，所以它通過代表兩張圖逐位元組相同。這次的改動只為了變快，所以參照是舊畫法；同一次改動也改了畫面時參照要換成什麼，寫在〔[效能最佳化的正確性要拿一份產生同樣畫面的參照實作逐格比](/report/optimization-equivalence-needs-a-reference-of-the-same-behavior/)〕。

比對只涵蓋取整的位移。smooth 的位移不取整，最近鄰取樣在非整數位置的樣子，這次沒有跟基準的畫法比對，也沒有開視窗用眼睛看過。

## 量測結果：改過的版本的每幀柵格化、build 與 CPU 取樣，跟基準比

基準是附錄的程式（每一幀重播背景與 41 叢的 `Picture`，換姿勢時 `setState`）；改過的版本有上面幾節的四處改動：葉叢拼成紋理圖集用 `drawRawAtlas` 畫、背景改成點陣圖、背景放進自己的 `RepaintBoundary`、姿勢經由 `ValueNotifier` 觸發重畫。量測的指令與 CPU 取樣照驅動方式比較那一篇的〈自動量測與 CPU 取樣〉：每一種驅動方式跑 12 秒、丟掉前 3 秒，後 9 秒是計數窗，CPU 每秒對 app 的行程取樣一次。2026-11-17 基準跑一次，改過的版本跑兩次，三次都在同一台 Mac、同一台螢幕上；三次的 `flutter run` 都印出 `Failed to foreground app; open returned 1`，app 視窗沒有被帶到最前面。基準只跑了一次，0.1 ms 這個量級的差距沒有量過雜訊。三次的 log 都印出 `Running with merged UI and platform thread. Experimental.`：這台機器上 UI 執行緒與平台執行緒是合併的（[Flutter Thread Model](/programming/flutter/knowledge-cards/flutter-thread-model/)）。

表裡的五種驅動方式照那一篇的定義：static 不動；smooth 用 `AnimationController` 每個 vsync 算一次姿勢；tickerStepped 用 `Ticker` 每個 vsync 醒來、姿勢 100 ms 才換；timerStepped 用 `Timer` 每 100 ms 算一次；eventDriven 平常不動，事件來了才起一陣 `Timer`。framework frame 是 framework 跑完一次版面、繪製與組圖層樹的次數，raster frame 是 engine 柵格化並送出一幀的次數。

基準的數字跟那一篇 2026-11-16 的兩次接近：smooth 每幀柵格化 3.71 ms（那一篇是 3.73 與 3.71 ms），CPU 取樣 61% 到 64%（那一篇是 58% 到 65%）；每幀 build 0.42 ms，比那一篇的 0.38 ms 多一點，下文比較的都是同一天的基準。

五種驅動方式每秒的 framework frame 與 paint 次數，三次之間相差在 0.2 次以內（smooth 的 framework frame 是 143.9、144.1、144.0）；raster frame 相差在 1.7 次以內，跳動的來源跟那一篇〈結果：兩次實測與預測的對照〉寫的一樣，是 engine 約 100 ms 一批回報 `FrameTiming`、一批跨過整秒邊界（推論）。繪製方式不改變幀數。

下表的每幀柵格化與每幀 build 是 `RESULT` 行的 `avgRaster` 與 `avgBuild`，分別來自 [FrameTiming](/programming/flutter/knowledge-cards/frame-timing/) 的 `rasterDuration` 與 `buildDuration`。`buildDuration` 從 framework 開始處理這一幀算起，到 framework 呼叫 `FlutterView.render` 把圖層樹交給 engine 為止（`dart:ui` 的文件寫 build 在 `FlutterView.render` 被呼叫時結束）。這一段全在 UI 執行緒上，包含動畫的回呼（例如 `Ticker` 的回呼）、rebuild、layout、繪製，以及 framework 把各圖層組成一棵圖層樹的那一步（`compositeFrame`）；raster 執行緒上的柵格化不在裡面。每一格的斜線前是改過的版本的第一次、後是第二次；CPU 取樣是那一次計數窗裡讀數的最小值到最大值：

| 驅動方式      | 基準：每幀柵格化 | 改過：每幀柵格化 | 基準：每幀 build | 改過：每幀 build | 基準：CPU 取樣 | 改過：CPU 取樣              |
| ------------- | ---------------- | ---------------- | ---------------- | ---------------- | -------------- | --------------------------- |
| smooth        | 3.71 ms          | 0.63 / 0.60 ms   | 0.42 ms          | 0.28 / 0.26 ms   | 61% 到 64%     | 22% 到 27% / 18% 到 27%     |
| tickerStepped | 3.96 ms          | 0.62 / 0.76 ms   | 0.10 ms          | 0.19 / 0.22 ms   | 61% 到 65%     | 23% 到 26% / 27% 到 30%     |
| timerStepped  | 10.69 ms         | 0.68 / 0.74 ms   | 1.17 ms          | 0.22 / 0.22 ms   | 12% 到 15%     | 2.2% 到 2.6% / 1.8% 到 2.2% |
| eventDriven   | 10.46 ms         | 0.91 / 0.92 ms   | 1.15 ms          | 0.22 / 0.25 ms   | 0% 到 13%      | 0.1% 到 4.3% / 0% 到 2.5%   |

eventDriven 的 CPU 取樣是整個計數窗的範圍，沒有像那一篇一樣拆成起風時與事件之間；最大值落在起風的那幾秒。static 在基準與改過的第一次都沒有排任何一幀；改過的第二次在計數窗裡有一幀 framework frame 與一幀 raster frame（平均每秒 0.1 幀），paint 是 0，所以這一幀沒有重畫葉叢，它從哪裡來，這次沒有查。

- **每幀柵格化降到原本的約五分之一到十六分之一**：每個 vsync 都排幀的 smooth 與 tickerStepped 從約 3.8 ms 降到 0.6 到 0.8 ms；一秒只排 10 幀左右的 timerStepped 與 eventDriven 從約 10.5 ms 降到 0.7 到 0.9 ms。那一篇〈跟簡化樹那一輪的對照〉寫的「低幀率時，平均每幀的柵格化時間比較長」，在基準是約 10.5 ms 對約 3.8 ms，改過之後縮到 0.7 到 0.9 ms 對 0.6 到 0.8 ms。那一篇列的候選成因（GPU 在低負載時降頻、每一幀之間快取變冷）這次一樣沒有量；這次的量測只顯示每一幀柵格化的工作變少之後，低幀率多出來的時間也跟著變少。
- **CPU 取樣：smooth、tickerStepped 與 timerStepped 這三種一直在擺動的方式都降了，timerStepped 降得比較多**：取樣平均（那一次計數窗裡讀數的平均）的變化是 smooth 從 63.0% 降到 25.0% 與 22.3%，tickerStepped 從 62.9% 降到 24.2% 與 28.7%，都是原本的四成左右；timerStepped 從 13.0% 降到 2.4% 與 2.0%，約六分之一。timerStepped 的 CPU 取樣平均除以 smooth 的，從基準的約五分之一（13.0 ÷ 63.0）變成約十分之一（2.2 ÷ 23.7，兩次的平均），比較接近兩者的幀數比（10.1 ÷ 144，約十四分之一）。把每幀 build 與柵格化的牆鐘時間加起來、乘上每秒幀數換算成每秒的量（取兩次的平均）：smooth 約 (0.27 + 0.62) × 144 ≈ 128 ms，timerStepped 約 (0.22 + 0.71) × 10.1 ≈ 9.4 ms，比值約十四分之一。跟那一篇〈跟簡化樹那一輪的對照〉的換算一樣，這只表示牆鐘時間與 CPU 取樣往同一個方向變化，不證明 CPU 花在哪一條執行緒。
- **每幀 build：smooth、timerStepped 與 eventDriven 降了**：smooth 從 0.42 降到 0.27 ms 左右，timerStepped 與 eventDriven 從約 1.16 降到約 0.22 ms。後兩者降了約 0.94 ms，比 smooth 在基準時整段 build 的 0.42 ms 還多，而 smooth 與 timerStepped 每一次換姿勢做的工作相同（算姿勢、rebuild、重畫），所以這 0.94 ms 大多不是省掉 rebuild 省下的。那一篇〈跟簡化樹那一輪的對照〉也寫了低幀率時每幀 build 比較長，這個差距在改過之後幾乎消失了（timerStepped 0.22 ms 對 smooth 0.27 ms），原因這次沒有量。那一篇列的候選成因是 CPU 在低負載時降頻、執行緒排到效率核心，這會把低幀率時每一幀的工作放慢；被放慢的工作裡，基準有一段是改過的版本沒有的：UI 執行緒在重畫時要處理被重播的 `Picture` 裡每一個矩形的邊界。smooth 每一幀也做這一段，整段 build 卻只有 0.42 ms，所以這一段單獨解釋不了 0.94 ms，要跟低負載時變慢一起成立（推論）。這一段的依據是 engine 原始碼：framework 錄繪圖指令用的 `PictureRecorder` 一律建立空間索引（`lib/ui/painting/picture_recorder.cc` 的 `prepare_rtree=true`），`drawPicture` 重播一張也有空間索引的 `Picture` 時，會把它每一個繪圖指令的邊界合併進來（`display_list/dl_builder.cc` 的 `DrawDisplayList`）；這一段花多少時間，這次沒有量。
- **每幀 build：tickerStepped 從 0.10 升到 0.19 與 0.22 ms，原因這次沒有查**：tickerStepped 一秒排 144 幀，大多數的幀沒有換姿勢、也不重畫，這些幀的 build 是 `Ticker` 的回呼（算姿勢、比較姿勢）加上組圖層樹那一步；沒有東西重畫時，framework 直接沿用外層 `RepaintBoundary` 的整個圖層，不往下走（`rendering/layer.dart` 的 `_addToSceneWithRetainedRendering`），所以改過的版本多了背景那一層，不太會增加這些幀的成本（推論）。基準只跑了一次，這 0.1 ms 的差距也可能在雜訊範圍內。
- **tickerStepped 與 smooth 的 CPU 取樣仍然分不出來**：讀者從取樣範圍分不出兩者，smooth 18% 到 27%，tickerStepped 23% 到 30%，兩者的範圍重疊。那一篇〈讀法：tickerStepped 的繪製次數與柵格化次數〉的結論在改過之後也成立：只減少繪製次數時，raster 執行緒仍然每秒柵格化 144 次。

葉叢圖集、背景點陣圖、背景獨立圖層與不 rebuild 是一起量的，每一處各佔多少，這次沒有拆開量。要拆的話，在程式裡加 `bool.fromEnvironment` 的開關（例如 `ATLAS`、`NOTIFIER`），依開關選 `TreePainter` 或兩個新的 painter、選 `setState` 或 `ValueNotifier`，每一種組合用 `--dart-define` 各跑一次自動量測（這個做法沒有實跑，demo 也沒有這兩個開關）。

## 這次場景的條件：搬到別的場景時對照 Texture Atlas 卡

這次的場景有幾個條件，自己的場景跟它不同時，結果可能不同：會動的 41 叢內容固定、每一幀只改位置；全場景每一幀要重播 11,046 個 `drawRect`（背景加葉叢）；基準每幀的時間大多在柵格化（smooth 的 build 0.42 ms、柵格化 3.71 ms），省下的是 CPU 用量，原本就沒有掉幀；畫面上只有這一個場景，`rasterDuration` 幾乎全屬於它；渲染後端是 Skia；每一格是整數的 4 個邏輯點（那台 144 Hz 螢幕的裝置像素比這次沒有記錄）。內容能不能事先畫好（含 sprite 影格）、圖塊多少、紋理尺寸上限、取樣方式與空隙、渲染後端各自怎麼改變結果，寫在 [Texture Atlas](/programming/flutter/knowledge-cards/texture-atlas/) 卡的〈判斷條件與後果〉；瓶頸在 raster 執行緒還是 UI 執行緒時先改哪一邊，寫在 [Flutter Thread Model](/programming/flutter/knowledge-cards/flutter-thread-model/) 卡的〈判斷條件與後果〉。

## 未量測的範圍：各處改動的貢獻、渲染後端、非整數的位移與像素比、app 視窗的像素、空隙與排寬

- **各處改動的貢獻**：葉叢圖集、背景點陣圖、背景獨立圖層與不 rebuild 是一起量的，預先柵格化與拼成圖集各省多少也分不出來；拆開量的做法寫在〈量測結果〉的最後一段。
- **渲染後端**：這次是 Skia。iOS 與 Android 的預設後端以官方文件為準；Impeller 沒有 raster cache，基準與降幅都可能不同，這次沒有量。
- **非整數的位移與像素比**：smooth 的位移不取整，最近鄰取樣在非整數位置的樣子沒有跟基準的畫法比對過，也沒有開視窗看過；裝置的像素比不是整數時兩種畫法的邊緣也沒有比對過。另一個原型在非整數位置上的一輪觀看結果，寫在〔[App 裡的裝飾性動畫：事件觸發的運動模型與重繪成本](/ux-design/06-interaction-feedback/event-driven-ambient-motion/)〕的〈跳格的畫風邊界〉，那是另一種繪製方式。
- **app 視窗的像素**：取整位移的比對是在 `flutter test` 的 CPU 柵格化環境裡做的，macOS app 視窗裡用 GPU 畫出的畫面沒有逐像素比對過。
- **空隙與排寬的取值**：`gap` 1 px 與 `maxWidth` 256 都沒有跟其他值比較過；不留空隙在這個場景會不會讀到隔壁的像素，沒有實跑。
- **其他的條件**：手機耗電、60 Hz 螢幕、執行緒拆分這些在驅動方式比較那一篇〈未量測的範圍〉列過，這次同樣沒有量。
