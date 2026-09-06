# nano_cust 言語仕様

## 概要

nano_cust は Scratch 3（`.sb3`）へコンパイルする、静的型付きの小さなオブジェクト指向言語です。ソースは **Class** と **Sprite** のみをトップレベルに置きます。`Main` Sprite の `main` 関数が Scratch の緑の旗を押したときの開始点になります。

この文書は、リポジトリにある現行コンパイラが実装している仕様を示します。

## コンパイル

```powershell
python main.py program.nc
python main.py program.nc -o game.sb3
python main.py program.nc --check
```

- 出力先を省略すると、入力ファイルと同じ名前で拡張子を `.sb3` にします。
- `--check` は構文解析と型検査だけを行い、出力ファイルは生成しません。
- エラー時は標準エラー出力に診断を表示し、終了コード `1` を返します。

## 最小プログラム

```text
sprite Main {
    fn main() -> int {
        Move(10, 20);
        return 0;
    }
}
```

`Main` Sprite は必須で、そこに `main` 関数を 1 つ宣言します。Sprite 内の関数は Scratch のカスタムブロックとして出力されます。

## 字句とコメント

- 識別子は英字または `_` で始まり、その後に英数字または `_` を続けられます。
- 整数、少数、二重引用符で囲んだ文字列を使えます。
- `//` から行末まではコメントです。
- 文末には `;` が必要です。ブロックは `{` と `}` で囲みます。

## 型

| 表記 | 内容 |
| --- | --- |
| `int` / `number` | Scratch の数値 |
| `string` | 文字列 |
| `boolean` | 比較・論理演算の結果に使われる真偽値 |
| `list T` | 要素型 `T` を持つ可変リスト |
| `ClassName` | ユーザー定義クラスのオブジェクト参照 |

変数と引数は常に型注釈が必要です。`int` は `number` の別名です。

```text
let score: int = 0;
let title: string = "nano";
let values: list int;
let player: Player = new Player;
```

初期値を省略したスカラー変数は、数値が `0`、文字列が空文字列、真偽値が false、オブジェクト参照が `0`（null 相当）になります。リストは空の状態で初期化されます。

## 宣言、代入、演算子

変数は `let name: Type` で宣言します。初期値は任意です。

```text
let x: int = 1;
x = x + 2;
```

演算子の優先順位（高い順）は、関数呼び出し・添字・メンバー参照、単項 `+`/`-`、`*`/`/`/`%`、`+`/`-`、比較、等価比較、`&&`、`||`、`=` です。代入先にできるのは変数、リスト要素、オブジェクトのフィールドです。

二項算術演算は同じ型の値どうしにだけ適用できます。比較演算は `boolean` を返します。

## 制御構文

```text
if score >= 100 {
    score = 0;
} elif score >= 50 {
    score = score + 1;
} else {
    score = score + 2;
}

while score < 10 {
    score = score + 1;
}
```

`if` と `while` の条件には `boolean` 型の式が必要です。各分岐・ループ本体には単一文またはブロックを置けます。

### リストの反復

```text
for value in values {
    Move(value, 0);
}
```

`for` の右辺は `list T` でなければなりません。反復変数の型は要素型 `T` です。反復回数はループ開始時のリスト長で固定されるため、本体で要素を追加しても、その追加分は同じループでは反復されません。

## 関数

```text
fn add(left: int, right: int) -> int {
    return left + right;
}
```

- 引数、戻り値ともに型注釈が必須です。
- 引数の個数と型は宣言に一致する必要があります。
- 関数本体は、すべての実行経路で `return` しなければなりません。
- 同じ Sprite 内の関数は前方参照できます。再帰呼び出しもサポートします。
- 別 Sprite の関数は `SpriteName.functionName(...)` として同期的に呼び出せます。

Scratch には通常の関数戻り値がないため、生成物は内部の戻り値領域とスタックを使って呼び出し・再帰を実現します。

## リスト

```text
let values: list int;
values.push(10);
values[0] = 20;
let last: int = values.pop();
```

| 操作 | 説明 |
| --- | --- |
| `values[index]` | 要素を読む |
| `values[index] = value` | 要素を書き換える |
| `values.push(value)` | 末尾に要素を追加する |
| `values.pop()` | 末尾の要素を取り出して削除する |

ソース上の添字は **0 始まり**です。Scratch のリスト添字は 1 始まりですが、コンパイラが変換します。範囲外アクセス・空リストへの `pop()` の動作は Scratch ランタイムに依存するため、プログラム側で避けてください。

リスト変数は Scratch のリストとして Sprite ごとに生成されます。ネストしたリスト型は型として書けますが、現在のバックエンドでは実用的な操作を保証していません。

## クラスとオブジェクト

```text
class Counter {
    let value: int;

    fn increment() -> int {
        value = value + 1;
        return value;
    }
}

sprite Main {
    fn main() -> int {
        let counter: Counter = new Counter;
        return counter.increment();
    }
}
```

クラスにはフィールドとメソッドを宣言できます。継承、コンストラクタ、アクセス修飾子はありません。

- オブジェクトは `new ClassName` で生成します。`new` の対象はクラス型でなければなりません。
- フィールドは `object.field` で読み書きできます。
- メソッドは `object.method(...)` で呼び出します。メソッド本体ではフィールド名を直接参照できます。
- クラスの各フィールドは、Scratch ではインスタンス位置に対応する専用リストに保存されます。
- クラスのリスト型フィールドは、現在のバックエンドでは未対応です。

## Sprite と Scratch 連携

各 `sprite Name { ... }` は、出力 `.sb3` 内の 1 つの Scratch Sprite になります。`Main.main` には「緑の旗が押されたとき」のイベントが付与されます。

次の組み込み関数は Scratch の標準ブロックへ直接変換されます。戻り値の型はすべて `number` です。

| 関数 | 引数 | Scratch の動作 |
| --- | --- | --- |
| `Move(x, y)` | `number, number` | x/y 座標へ移動 |
| `MoveSteps(steps)` | `number` | 歩数ぶん動かす |
| `TurnRight(degrees)` | `number` | 右に回す |
| `TurnLeft(degrees)` | `number` | 左に回す |
| `SetDirection(direction)` | `number` | 向きを設定 |
| `PenDown()` | なし | ペンを下ろす |
| `PenUp()` | なし | ペンを上げる |
| `PenColor(color)` | `string` | ペンの色を設定 |
| `PenSize(size)` | `number` | ペンの太さを設定 |
| `ClearPen()` | なし | ペンの描画を消去 |

ペン用の関数を使った場合、出力プロジェクトには Pen 拡張が追加されます。

## `save` / `unsave`

```text
save object;
unsave object;
```

`save` と `unsave` はオブジェクト参照を内部の保持登録から外す／登録するための文です。現行実装ではオブジェクトの解放そのものや自動的な寿命管理はまだ提供していません。通常のクラス利用では不要であり、将来の RAII・オブジェクト管理機能に向けた低レベル操作です。

## 現在の制約

- トップレベルに置けるのは `class` と `sprite` だけです。
- `import`、`none`、`null` などの予約字は、現行パーサーではプログラムの構文として利用できません。
- 真偽値リテラルは未実装です。比較や論理演算の結果を条件に使ってください。
- リストの要素アクセス、代入、メソッド呼び出しのレシーバーは名前付きリスト変数である必要があります。
- オブジェクトのリスト型フィールド、継承、コンストラクタ、GC は未実装です。
