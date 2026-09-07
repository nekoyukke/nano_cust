# nano_cust 言語仕様

## 1. 概要

nano_cust は Scratch 3（`.sb3`）へコンパイルする静的型付き言語です。ソースファイルのトップレベルには `class` と `sprite` だけを記述できます。`sprite Main` の `main` 関数が、Scratch の緑の旗を押したときの開始点です。

この文書は、現在のコンパイラで利用できる構文を説明します。

## 2. コンパイル

```powershell
python main.py program.nc
python main.py program.nc -o game.sb3
python main.py program.nc --check
```

- 出力先を省略すると、入力ファイルと同じ場所に `.sb3` を作ります。
- `--check` は出力を作らず、構文と型を検証します。
- エラー時は標準エラー出力に診断を表示し、終了コード `1` を返します。
- `--force-type` は Scratch の型変換を許可するための上級者向けオプションです。

## 3. 最小プログラム

```text
sprite Main {
    fn main() -> int {
        Move(10, 20);
        return 0;
    }
}
```

`Main` Sprite は必須です。関数の本体はすべての実行経路で `return` する必要があります。

## 4. 字句・コメント

- 識別子は英字または `_` で始まり、英数字と `_` を続けられます。
- 整数、小数、二重引用符で囲んだ文字列を使えます。
- `//` から行末まではコメントです。
- 文の終わりには `;` を置きます。ブロックは `{` と `}` で囲みます。

```text
// プレイヤーの初期位置
let title: string = "nano_cust";
let score: int = 0;
```

## 5. 型と変数

| 表記 | 内容 | 初期値 |
| --- | --- | --- |
| `int` / `number` | Scratch の数値 | `0` |
| `string` | 文字列 | `""` |
| `boolean` | 比較・論理演算の結果 | `0`（false 相当） |
| `list T` | 要素型 `T` を持つ可変リスト | 空リスト |
| `ClassName` | ユーザー定義クラスへの参照 | `0`（null 相当） |

変数と引数には型注釈が必要です。`int` は `number` の別名です。

```text
let score: int = 0;
let name: string = "Player";
let positions: list number;
let player: Player = new Player;
```

内部では null 相当のオブジェクト参照を `0` として表現します。現時点で `null` はソースのリテラルとしては使えないため、未初期化のオブジェクト参照を利用する前には必ず `new` で生成してください。

## 6. 式と代入

```text
let x: int = 1;
x = x + 2;
```

| 種類 | 演算子 |
| --- | --- |
| 単項 | `+x`, `-x` |
| 算術 | `+`, `-`, `*`, `/`, `%` |
| 比較 | `<`, `<=`, `>`, `>=`, `==`, `!=` |
| 論理 | `&&`, `||` |
| 代入 | `=` |

演算子の優先順位は、呼び出し・添字・メンバー参照、単項、乗除算、加減算、比較、等価比較、`&&`、`||`、代入の順です。算術演算は数値型、論理演算は boolean 型に適用します。代入先にできるのは変数、リスト要素、オブジェクトのフィールドです。

## 7. 制御構文

```text
if score >= 100 {
    score = 0;
} elif score >= 50 {
    score = score + 1;
} else {
    score = score + 2;
}

while score < 10 && score != 5 {
    score = score + 1;
}
```

`if` と `while` の条件には boolean 型の式が必要です。各分岐とループ本体には、単一文またはブロックを置けます。

### リストの反復

```text
for value in values {
    Move(value, 0);
}
```

`for` の右辺は `list T` でなければなりません。反復変数の型は要素型 `T` です。反復回数はループ開始時のリスト長で決まるため、ループ中に要素を追加しても、その追加分は同じループでは処理されません。

## 8. 関数

```text
fn add(left: int, right: int) -> int {
    return left + right;
}
```

- 引数と戻り値には型注釈が必要です。
- 呼び出し時の引数の個数と型は宣言に一致させます。
- 同じ Sprite 内の関数は前方参照と再帰呼び出しをサポートします。
- 別 Sprite の関数は `SpriteName.functionName(...)` の形で同期呼び出しできます。

Scratch のカスタムブロックには戻り値がないため、コンパイラは内部のスタックと戻り値領域を使って関数呼び出しを実現します。

## 9. リスト

```text
let values: list int;
values.push(10);
values[0] = 20;
let last: int = values.pop();
let count: int = values.length();
```

| 操作 | 説明 |
| --- | --- |
| `values[index]` | 要素を読む |
| `values[index] = value` | 要素を書き換える |
| `values.push(value)` | 末尾に要素を追加する |
| `values.pop()` | 末尾の要素を取り出して削除する |
| `values.length()` | 現在の要素数を返す |

添字は **0 始まり**です。Scratch のリストは 1 始まりですが、コンパイラが変換します。範囲外アクセスと空リストへの `pop()` は避けてください。ネストしたリスト型は宣言できますが、実用的な操作はまだ保証されません。

## 10. クラスとオブジェクト

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

- `new ClassName` でオブジェクトを生成します。
- フィールドは `object.field` で読み書きします。
- メソッドは `object.method(...)` で呼び出します。メソッド本体ではフィールド名を直接参照できます。
- フィールドの値は Scratch のリストに保存されます。

継承、コンストラクタ、アクセス修飾子、GC はありません。クラスのリスト型フィールドも未対応です。

## 11. Sprite と Scratch の組み込み関数

各 `sprite Name { ... }` は、出力 `.sb3` の 1 つの Sprite になります。`Main.main` には緑の旗イベントが付与されます。

| 関数 | 引数 | Scratch での動作 |
| --- | --- | --- |
| `Move(x, y)` | `number, number` | 指定座標へ移動 |
| `MoveSteps(steps)` | `number` | 指定歩数だけ動く |
| `TurnRight(degrees)` | `number` | 右に回す |
| `TurnLeft(degrees)` | `number` | 左に回す |
| `SetDirection(direction)` | `number` | 向きを設定 |
| `PenDown()` | なし | ペンを下ろす |
| `PenUp()` | なし | ペンを上げる |
| `PenColor(color)` | `string` | ペンの色を設定 |
| `PenSize(size)` | `number` | ペンの太さを設定 |
| `ClearPen()` | なし | ペンの描画を消す |
| `KeyPressed(key)` | `string` | 指定キーが押されているか（`boolean`） |
| `MousePressed()` | なし | マウスボタンが押されているか（`boolean`） |
| `MouseX()` | なし | マウスポインタの X 座標 |
| `MouseY()` | なし | マウスポインタの Y 座標 |
| `Sin(degrees)` | `number` | 指定角度の正弦 |
| `Cos(degrees)` | `number` | 指定角度の余弦 |
| `Tan(degrees)` | `number` | 指定角度の正接 |

ペン関数を使うと、出力プロジェクトには Pen 拡張が自動的に追加されます。

入力は毎フレーム、またはループ内で読むのが基本です。例えば次のように書けます。

```text
if KeyPressed("ArrowRight") { Move(MouseX(), MouseY()); }
```

三角関数の角度はラジアンではなく、Scratchと同じ**度数法**です。例えば `Sin(30)` は `0.5` になります。

## 12. `save` と `unsave`

```text
save object;
unsave object;
```

これらはオブジェクト参照を内部の保持登録から外す／登録する低レベル操作です。オブジェクトの解放や自動寿命管理は行いません。通常のプログラムでは使用不要です。

## 13. 現在の制約

- トップレベルに置けるのは `class` と `sprite` だけです。
- `import` は未実装です。
- `true` / `false` の真偽値リテラルは未実装です。比較や `&&`、`||` の結果を条件に使ってください。
- `null` / `none` は予約されていますが、ソースのリテラルとしては未実装です。
- リスト操作の対象は名前付きリスト変数である必要があります。
- クラスのリスト型フィールド、継承、コンストラクタ、GC は未実装です。
