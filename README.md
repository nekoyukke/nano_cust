# nano_cust

**nano_cust** は、Scratch 3 プロジェクト（`.sb3`）へコンパイルする、小さな静的型付きプログラミング言語です。Sprite、関数、リスト、クラスを使って、Scratch の見た目を保ちながらテキストでゲームや図形を記述できます。

> このプロジェクトは開発中です。言語機能と生成される Scratch プロジェクトの形式は、今後変わる可能性があります。

## できること

- `.nc` ソースから Scratch 3 の `.sb3` を生成
- Sprite ごとの関数と、Sprite 間の同期呼び出し
- 数値・文字列・真偽値・リスト・クラス型
- 条件分岐、ループ、再帰
- Scratch の移動・ペンブロックを組み込み関数として利用

## はじめ方

Python 3.10 以降を用意し、リポジトリのルートで実行します。

```powershell
# 構文・型だけ確認する
python main.py examples\mandelbrot.nc --check

# Scratch プロジェクトを生成する
python main.py examples\mandelbrot.nc -o mandelbrot.sb3
```

生成した `.sb3` を Scratch Desktop または [Scratch](https://scratch.mit.edu/) で開き、緑の旗を押してください。

## 最小例

```text
sprite Main {
    fn main() -> int {
        Move(80, 40);
        return 0;
    }
}
```

`Main.main` が緑の旗から実行されます。`Move` は Scratch の「x 座標を、y 座標を」に変換されます。

## サンプル

[マンデルブロー集合](examples/mandelbrot.nc)は、ペンでフラクタルを描画するサンプルです。`&&`、入れ子の `while`、小数演算、ペン操作をまとめて確認できます。

## コマンドライン

```text
python main.py INPUT [-o OUTPUT] [--check] [--force-type]
```

| オプション | 説明 |
| --- | --- |
| `-o`, `--output` | 出力する `.sb3` のパス。省略時は入力と同じ名前で拡張子を `.sb3` にします。 |
| `--check` | `.sb3` を作らず、字句解析・構文解析・意味解析・型検査だけを行います。 |
| `--force-type` | Scratch の暗黙変換に任せる型の組み合わせを許可します。通常は使わず、まず型エラーを解消してください。 |

## 開発者向け

テストは標準ライブラリの `unittest` で実行できます。

```powershell
python -m unittest discover -s test -p "test_*.py" -v
```

生成物の構造、再帰呼び出し、Sprite 間呼び出し、リスト、組み込みブロックをテストしています。

## ドキュメント

言語の構文、型、Scratch 連携、現在の制約は[言語仕様](docs/language.md)を参照してください。
