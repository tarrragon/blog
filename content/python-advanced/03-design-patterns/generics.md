---
title: "3.5.1 泛型進階"
date: 2026-01-20
description: "TypeVar 進階用法、Generic 類別、Protocol 與結構化子型別"
weight: 1
---

# 泛型進階

入門系列介紹了 `TypeVar` 的基本用法。本章深入探討泛型的進階特性，讓你能夠建立型別安全的抽象層。

## 先備知識

- 入門系列 [2.2 Optional、Union、泛型](../../python/02-type-system/optional-union/)

## TypeVar 進階

### bound 參數

`bound` 限制 TypeVar 必須是某個型別的子型別：

```python
from typing import TypeVar

class Animal:
    def speak(self) -> str:
        return "..."

class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"

class Cat(Animal):
    def speak(self) -> str:
        return "Meow!"

# T 必須是 Animal 或其子類別
T = TypeVar("T", bound=Animal)

def make_speak(animal: T) -> str:
    return animal.speak()  # 型別檢查器知道 animal 有 speak() 方法

# 正確使用
make_speak(Dog())  # OK
make_speak(Cat())  # OK

# 錯誤使用
make_speak("not an animal")  # 型別錯誤
```

### bound vs 限制型別

```python
from typing import TypeVar

# 方式一：bound - T 可以是 Animal 或任何子類別
T_bound = TypeVar("T_bound", bound=Animal)

# 方式二：限制型別 - T 只能是 Dog 或 Cat，不能是其他 Animal 子類別
T_constrained = TypeVar("T_constrained", Dog, Cat)
```

差異：

| 方式 | 適用情況 |
|------|---------|
| `bound=Animal` | T 可以是 Animal 或任何子類別（包括未來新增的） |
| `TypeVar("T", Dog, Cat)` | T 只能是明確列出的型別 |

### covariant 與 contravariant

這是泛型最難理解的概念，但對於設計型別安全的 API 非常重要。

#### 問題情境

```python
class Animal:
    pass

class Dog(Animal):
    pass

# 問題：List[Dog] 是 List[Animal] 的子型別嗎？
def process_animals(animals: list[Animal]) -> None:
    animals.append(Animal())  # 如果傳入 list[Dog]，這會破壞型別安全

dogs: list[Dog] = [Dog(), Dog()]
process_animals(dogs)  # 如果允許，dogs 裡面會有 Animal！
```

Python 的 `list` 是**不變的**（invariant），所以 `list[Dog]` 不是 `list[Animal]` 的子型別。

#### covariant（協變）

只讀的容器可以是協變的：

```python
from typing import TypeVar, Generic, Iterator

T_co = TypeVar("T_co", covariant=True)

class ReadOnlyBox(Generic[T_co]):
    """只能讀取，不能修改"""
    def __init__(self, value: T_co) -> None:
        self._value = value

    def get(self) -> T_co:
        return self._value

# ReadOnlyBox[Dog] 是 ReadOnlyBox[Animal] 的子型別
def show_animal(box: ReadOnlyBox[Animal]) -> None:
    print(box.get())

dog_box: ReadOnlyBox[Dog] = ReadOnlyBox(Dog())
show_animal(dog_box)  # OK - Dog 是 Animal
```

**記憶方式**：協變 = 輸出方向，子型別可以替代父型別。

#### contravariant（逆變）

只寫的容器可以是逆變的：

```python
from typing import TypeVar, Generic

T_contra = TypeVar("T_contra", contravariant=True)

class Handler(Generic[T_contra]):
    """處理器：只接收值"""
    def handle(self, value: T_contra) -> None:
        print(f"Handling: {value}")

# Handler[Animal] 是 Handler[Dog] 的子型別！（反直覺）
def setup_dog_handler(handler: Handler[Dog]) -> None:
    handler.handle(Dog())

animal_handler: Handler[Animal] = Handler()
setup_dog_handler(animal_handler)  # OK - 能處理 Animal 就能處理 Dog
```

**記憶方式**：逆變 = 輸入方向，父型別可以替代子型別。

#### 實際應用

```python
from typing import Callable

# Callable 的參數是逆變的，返回值是協變的
# Callable[[Animal], Dog] 是 Callable[[Dog], Animal] 的子型別

def process(func: Callable[[Dog], Animal]) -> None:
    result = func(Dog())
    print(result)

def any_animal_to_dog(animal: Animal) -> Dog:
    return Dog()

process(any_animal_to_dog)  # OK
```

## Generic 類別

### 建立自己的泛型容器

```python
from typing import TypeVar, Generic, Optional

T = TypeVar("T")

class Stack(Generic[T]):
    """型別安全的堆疊"""

    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> Optional[T]:
        if self._items:
            return self._items.pop()
        return None

    def peek(self) -> Optional[T]:
        if self._items:
            return self._items[-1]
        return None

# 使用
int_stack: Stack[int] = Stack()
int_stack.push(1)
int_stack.push(2)
int_stack.push("three")  # 型別錯誤！

str_stack: Stack[str] = Stack()
str_stack.push("hello")
```

### 多型別參數

```python
from typing import TypeVar, Generic

K = TypeVar("K")
V = TypeVar("V")

class Pair(Generic[K, V]):
    """鍵值對"""

    def __init__(self, key: K, value: V) -> None:
        self.key = key
        self.value = value

    def swap(self) -> "Pair[V, K]":
        return Pair(self.value, self.key)

# 使用
pair: Pair[str, int] = Pair("age", 25)
swapped: Pair[int, str] = pair.swap()
```

### 繼承泛型類別

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

# 方式一：保持泛型
class Box(Container[T]):
    def unwrap(self) -> T:
        return self.value

# 方式二：具體化型別
class StringBox(Container[str]):
    def upper(self) -> str:
        return self.value.upper()
```

## Protocol 與結構化子型別

### 什麼是 Protocol？

Protocol 定義「介面」，任何實現該介面的類別都被視為符合該 Protocol，無需明確繼承。

```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> str:
        ...

# 這個類別沒有繼承 Drawable，但符合 Protocol
class Circle:
    def draw(self) -> str:
        return "○"

class Square:
    def draw(self) -> str:
        return "□"

def render(shape: Drawable) -> None:
    print(shape.draw())

render(Circle())  # OK - Circle 有 draw() 方法
render(Square())  # OK - Square 有 draw() 方法
```

### Protocol vs ABC

| 特性 | Protocol | ABC |
|------|----------|-----|
| 繼承要求 | 不需要 | 需要 |
| 型別檢查 | 結構化（duck typing） | 名義上（nominal） |
| 執行期檢查 | 需要 `runtime_checkable` | 內建 |
| 適用場景 | 第三方類別、鬆散耦合 | 自己控制的類別層級 |

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

# ABC 方式
class DrawableABC(ABC):
    @abstractmethod
    def draw(self) -> str:
        ...

class CircleABC(DrawableABC):  # 必須繼承
    def draw(self) -> str:
        return "○"

# Protocol 方式
@runtime_checkable
class DrawableProtocol(Protocol):
    def draw(self) -> str:
        ...

class CircleProtocol:  # 不需要繼承
    def draw(self) -> str:
        return "○"

# 執行期檢查
print(isinstance(CircleProtocol(), DrawableProtocol))  # True
```

### 何時選擇 Protocol？

```python
# 使用 Protocol 的情況：

# 1. 處理第三方類別
class JSONSerializable(Protocol):
    def to_json(self) -> str:
        ...

# 第三方類別可能已經有 to_json()，不需要修改它們

# 2. 定義回調介面
class EventHandler(Protocol):
    def on_event(self, event: dict) -> None:
        ...

# 任何有 on_event 方法的類別或函式都可以使用

# 3. 鬆散耦合
class Closeable(Protocol):
    def close(self) -> None:
        ...

def cleanup(resource: Closeable) -> None:
    resource.close()

# 檔案、連接、任何有 close() 的東西都可以用
```

### 帶有屬性的 Protocol

```python
from typing import Protocol

class Named(Protocol):
    name: str  # 只需要有這個屬性

class Person:
    def __init__(self, name: str) -> None:
        self.name = name

class Company:
    name: str = "Acme Corp"

def greet(entity: Named) -> str:
    return f"Hello, {entity.name}!"

greet(Person("Alice"))  # OK
greet(Company())        # OK
```

## 實際範例：型別安全的 Repository 介面

結合以上所有概念，建立一個型別安全的資料存取層：

```python
from typing import TypeVar, Generic, Protocol, Optional
from abc import abstractmethod

# 定義實體必須有 id 屬性
class HasId(Protocol):
    id: int

# 泛型 Repository 介面
T = TypeVar("T", bound=HasId)

class Repository(Generic[T]):
    """資料存取層的抽象介面"""

    @abstractmethod
    def get(self, id: int) -> Optional[T]:
        """根據 ID 取得實體"""
        ...

    @abstractmethod
    def save(self, entity: T) -> T:
        """儲存實體"""
        ...

    @abstractmethod
    def delete(self, id: int) -> bool:
        """刪除實體"""
        ...

    @abstractmethod
    def find_all(self) -> list[T]:
        """取得所有實體"""
        ...

# 具體實現
class User:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name

class InMemoryUserRepository(Repository[User]):
    """記憶體中的 User Repository"""

    def __init__(self) -> None:
        self._storage: dict[int, User] = {}
        self._next_id = 1

    def get(self, id: int) -> Optional[User]:
        return self._storage.get(id)

    def save(self, entity: User) -> User:
        if entity.id == 0:
            entity.id = self._next_id
            self._next_id += 1
        self._storage[entity.id] = entity
        return entity

    def delete(self, id: int) -> bool:
        if id in self._storage:
            del self._storage[id]
            return True
        return False

    def find_all(self) -> list[User]:
        return list(self._storage.values())

# 使用
def process_user(repo: Repository[User], user_id: int) -> None:
    user = repo.get(user_id)
    if user:
        print(f"Found user: {user.name}")

# 型別安全：不能把 UserRepository 傳給需要 Repository[Product] 的函式
```

## 常見錯誤

### 1. 忘記 TypeVar 的名稱參數

```python
# 錯誤
T = TypeVar()  # TypeError

# 正確
T = TypeVar("T")
```

### 2. 在類別方法中重複定義 TypeVar

```python
T = TypeVar("T")

class Box(Generic[T]):
    # 錯誤：方法內重新定義 T
    def transform(self, func: Callable[[T], T]) -> T:
        T2 = TypeVar("T2")  # 這是不同的 TypeVar！
        ...

    # 正確：直接使用類別的 T
    def transform(self, func: Callable[[T], T]) -> T:
        return func(self.value)
```

### 3. 誤用 covariant/contravariant

```python
T_co = TypeVar("T_co", covariant=True)

class MutableBox(Generic[T_co]):  # 錯誤！
    def __init__(self, value: T_co) -> None:
        self._value = value

    def set(self, value: T_co) -> None:  # 協變型別不能用在參數位置
        self._value = value
```

## 小結

| 概念 | 用途 |
|------|------|
| `bound` | 限制 TypeVar 必須是某型別的子型別 |
| `covariant` | 只讀容器，子型別可替代父型別 |
| `contravariant` | 只寫容器，父型別可替代子型別 |
| `Generic[T]` | 建立泛型類別 |
| `Protocol` | 結構化子型別，不需繼承 |

## 思考題

1. 為什麼 `list` 是不變的而不是協變的？
2. 什麼情況下應該用 Protocol 而不是 ABC？
3. 如何為一個既可讀又可寫的容器設計型別安全的介面？

---

*下一章：[3.5.2 異常設計架構](../exception-design/)*
