---
title: "flutter 可以使用的 togglebutton 樣式"
date: 2025-09-09
draft: false
tags: ["flutter"]
---

## 有製作切換選項的按鈕需求，查詢之後得到三種可用的樣式

1. ToggleButtons

{{< figure src="/work-log/flutter_toggle_button/ToggleButtons.png" alt="ToggleButtons 樣式" >}}

```dart
ToggleButtons(
  isSelected: [controller.isFirstSelected, controller.isSecondSelected],
  onPressed: (int index) {
    controller.toggleSelection(index);
  },
  children: [
    Text('選項一'),
    Text('選項二'),
  ],
  selectedColor: Colors.white,
  fillColor: Colors.blue,
  borderColor: Colors.blue,
  borderRadius: BorderRadius.circular(8),
)
```

1. SegmentedButton (Flutter 3.12+)

{{< figure src="/work-log/flutter_toggle_button/SegmentedButton.png" alt="SegmentedButton 樣式" >}}

```dart
SegmentedButton<String>(
  segments: [
    ButtonSegment(value: 'option1', label: Text('選項一')),
    ButtonSegment(value: 'option2', label: Text('選項二')),
  ],
  selected: {controller.selectedOption},
  onSelectionChanged: (Set<String> newSelection) {
    controller.updateSelection(newSelection.first);
  },
)
```

1. CupertinoSlidingSegmentedControl (iOS 風格)

{{< figure src="/work-log/flutter_toggle_button/CupertinoSlidingSegmentedControl.png" alt="CupertinoSlidingSegmentedControl 樣式" >}}

```dart
CupertinoSlidingSegmentedControl<String>(
  children: {
    'option1': Text('選項一'),
    'option2': Text('選項二'),
  },
  groupValue: controller.selectedOption,
  onValueChanged: (String? value) {
    controller.updateSelection(value!);
  },
)
```
