// 透過 VM service 在執行中的 Flutter APP 裡求值，用來在截圖前切換畫面。
//
// 用法（通常經由同目錄的 drive.sh 呼叫）：
//   dart --packages=<APP>/.dart_tool/package_config.json drive.dart <ws-uri> push <route> [arg]
//   ... tap <x> <y>        點一下，座標是邏輯座標（截圖像素 ÷ 裝置像素比）
//   ... longpress <x> <y>  按住 700ms
//   ... drag <x1> <y1> <x2> <y2>  從第一點拖到第二點，約 300ms（捲動清單用；往上拖是往下捲）
//   ... back               對前序走訪最後找到的 Navigator 呼叫 maybePop()
//   ... type <text>        把文字寫進目前有焦點的輸入框（取代原內容）
//   ... dpr                印出裝置像素比（截圖像素 ÷ 這個值 ＝ 邏輯座標）
//
// push、back、type、dpr 要在一個 import 了 Flutter widgets 的 APP 函式庫裡求值。
// 預設用 isolate 的根函式庫（flutter run 啟動的那一個）；取不到時找第一個 package: 開頭、
// /main.dart 結尾、不屬於 flutter 套件的函式庫。要換一個函式庫時，用環境變數 FLUTTER_DRIVE_LIB 指定完整 uri。
// push 的路由與引數、type 的文字先經 dartLiteral() 跳脫，再嵌進求值的字串。
// 求值要 debug 模式：profile 與 release 沒有 expression evaluation。
import 'dart:io';

import 'package:vm_service/vm_service.dart';
import 'package:vm_service/vm_service_io.dart';

const gestureLib = 'package:flutter/src/gestures/binding.dart';

String findAppLib(List<LibraryRef> libs, LibraryRef? rootLib) {
  final fromEnv = Platform.environment['FLUTTER_DRIVE_LIB'];
  if (fromEnv != null && fromEnv.isNotEmpty) return fromEnv;
  // 優先用 isolate 的根函式庫（flutter run 啟動的那一個，通常是 lib/main.dart）
  final rootUri = rootLib?.uri;
  if (rootUri != null && rootUri.startsWith('package:') && !rootUri.startsWith('package:flutter/')) {
    return rootUri;
  }
  final main = libs.where((l) {
    final uri = l.uri ?? '';
    return uri.startsWith('package:') &&
        uri.endsWith('/main.dart') &&
        !uri.startsWith('package:flutter/');
  });
  if (main.isEmpty) {
    stderr.writeln('找不到 APP 的 main.dart，請用 FLUTTER_DRIVE_LIB 指定函式庫 uri');
    exit(2);
  }
  return main.first.uri!;
}

// 把任意文字寫成 Dart 的單引號字串字面值（跳脫反斜線、單引號、$ 與換行）
String dartLiteral(String s) =>
    "'${s.replaceAll(r'\', r'\\').replaceAll("'", r"\'").replaceAll(r'$', r'\$').replaceAll('\n', r'\n').replaceAll('\r', r'\r')}'";

// 座標引數必須是數字，數量要夠；不符時印用法、exit 2，不送出求值
List<num> coords(List<String> args, int from, int count) {
  final out = <num>[];
  for (var i = from; i < from + count; i++) {
    final v = i < args.length ? num.tryParse(args[i]) : null;
    if (v == null || !v.isFinite) {
      stderr.writeln('${args[1]} 要 $count 個數字座標（邏輯座標），收到：${args.skip(2).join(' ')}');
      exit(2);
    }
    out.add(v);
  }
  return out;
}

// 從根元素前序走訪，取最後找到的 NavigatorState。單層 Navigator 的 APP 取到的就是它。
// 有巢狀 Navigator（分頁殼、CupertinoTabScaffold、go_router 的 ShellRoute）時，取到的可能是
// 沒有顯示的分頁、或被蓋住的頁面底下那一個 Navigator，push 與 back 會改到看不見的狀態；
// 這類 APP 不用 push 與 back，改用 tap 點畫面上的入口與返回鍵。
const findNavigator =
    'NavigatorState? nav; void visit(Element e) { if (e is StatefulElement && e.state is NavigatorState) { nav = e.state as NavigatorState; } e.visitChildren(visit); } WidgetsBinding.instance.rootElement!.visitChildren(visit);';

Future<void> main(List<String> args) async {
  if (args.length < 2) {
    stderr.writeln('用法：drive.dart <ws-uri> <push|tap|longpress|drag|back|type|dpr> ...');
    exit(2);
  }
  final pointArgs = {'tap': 2, 'longpress': 2, 'drag': 4}[args[1]];
  final points = pointArgs == null ? const <num>[] : coords(args, 2, pointArgs);
  if (args[1] == 'push' && args.length < 3) {
    stderr.writeln('push 要一個路由名，例如 push /browse');
    exit(2);
  }
  final service = await vmServiceConnectUri(args[0]);
  final vm = await service.getVM();
  final isolate = vm.isolates!.firstWhere((i) => i.name == 'main');
  final isolateObj = await service.getIsolate(isolate.id!);
  final libs = isolateObj.libraries!;
  final isGesture = pointArgs != null;
  final want = isGesture ? gestureLib : findAppLib(libs, isolateObj.rootLib);
  final libRef = libs.firstWhere(
    (l) => l.uri == want,
    orElse: () {
      stderr.writeln('isolate 裡沒有函式庫 $want');
      exit(2);
    },
  );

  String expr;
  switch (args[1]) {
    case 'push':
      final arg = args.length > 3 ? dartLiteral(args[3]) : 'null';
      expr =
          "(() { $findNavigator nav!.pushNamed(${dartLiteral(args[2])}, arguments: $arg); return 'pushed'; })()";
    case 'back':
      expr = "(() { $findNavigator nav!.maybePop(); return 'back'; })()";
    case 'dpr':
      expr = "WidgetsBinding.instance.platformDispatcher.views.first.devicePixelRatio.toString()";
    case 'tap':
    case 'longpress':
      final x = points[0], y = points[1];
      final hold = args[1] == 'longpress' ? 700 : 60;
      expr =
          "(() { final p = Offset($x, $y); GestureBinding.instance.handlePointerEvent(PointerDownEvent(pointer: 91, position: p)); Future.delayed(const Duration(milliseconds: $hold), () => GestureBinding.instance.handlePointerEvent(PointerUpEvent(pointer: 91, position: p))); return '${args[1]}'; })()";
    case 'drag':
      // 拖曳辨識讀的是每一筆 PointerMoveEvent 的 delta，所以每一步都帶上位移量
      final steps = 12;
      final dx = (points[2] - points[0]) / steps, dy = (points[3] - points[1]) / steps;
      expr =
          "(() { final a = Offset(${points[0]}, ${points[1]}); final d = Offset($dx, $dy); final g = GestureBinding.instance; g.handlePointerEvent(PointerDownEvent(pointer: 92, position: a)); for (var i = 1; i <= $steps; i++) { final p = a + d * i.toDouble(); Future.delayed(Duration(milliseconds: i * 25), () => g.handlePointerEvent(PointerMoveEvent(pointer: 92, position: p, delta: d))); } Future.delayed(const Duration(milliseconds: ${steps * 25 + 25}), () => g.handlePointerEvent(PointerUpEvent(pointer: 92, position: a + d * $steps.0))); return 'drag'; })()";
    case 'type':
      final text = args.sublist(2).join(' ');
      expr =
          "(() { final f = FocusManager.instance.primaryFocus; EditableTextState? s; void visit(Element e) { if (e is StatefulElement && e.state is EditableTextState && (e.state as EditableTextState).widget.focusNode == f) { s = e.state as EditableTextState; } e.visitChildren(visit); } WidgetsBinding.instance.rootElement!.visitChildren(visit); s!.userUpdateTextEditingValue(TextEditingValue(text: ${dartLiteral(text)}, selection: TextSelection.collapsed(offset: ${text.length})), SelectionChangedCause.keyboard); return 'typed'; })()";
    default:
      stderr.writeln('未知的指令：${args[1]}');
      exit(2);
  }
  final r = await service.evaluate(isolate.id!, libRef.id!, expr);
  if (r is ErrorRef) {
    stderr.writeln('求值失敗：${r.message}');
    await service.dispose();
    exit(1);
  }
  print(r is InstanceRef ? r.valueAsString : r);
  await service.dispose();
}
