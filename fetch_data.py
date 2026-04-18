"""
Tatoeba インドネシア語↔日本語ペア取得スクリプト
データ: Tatoeba (https://tatoeba.org) CC BY 2.0
"""

import urllib.request
import bz2
import tarfile
import csv
import json
import os
import io
import sys

OUT_PATH   = os.path.join(os.path.dirname(__file__), "data", "data.json")
CACHE_DIR  = os.path.join(os.path.dirname(__file__), "data", "_cache")

URLS = {
    "ind": "https://downloads.tatoeba.org/exports/per_language/ind/ind_sentences.tsv.bz2",
    "jpn": "https://downloads.tatoeba.org/exports/per_language/jpn/jpn_sentences.tsv.bz2",
    "links": "https://downloads.tatoeba.org/exports/links.tar.bz2",
}

MAX_PAIRS = 1000   # 上限（多すぎるとJSONが重くなる）
MIN_LEN   = 3      # インドネシア語の最低文字数
MAX_LEN   = 80     # インドネシア語の最大文字数


def download(name, url):
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        print(f"  キャッシュを使用: {name}")
        return path
    print(f"  ダウンロード中: {name} ({url})")
    urllib.request.urlretrieve(url, path, reporthook=_progress)
    print()
    return path


def _progress(count, block, total):
    mb = count * block / 1024 / 1024
    total_mb = total / 1024 / 1024 if total > 0 else "?"
    print(f"\r    {mb:.1f} MB / {total_mb:.1f} MB", end="", flush=True)


def load_sentences_bz2(path):
    """TSV.bz2 → {id: text} の辞書を返す"""
    sentences = {}
    with bz2.open(path, "rt", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) >= 3:
                sentences[int(row[0])] = row[2]
    return sentences


def load_links(path):
    """links.tar.bz2 → [(id1, id2)] のリストを返す"""
    links = []
    with tarfile.open(path, "r:bz2") as tar:
        member = tar.getmember("links.csv")
        f = tar.extractfile(member)
        reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t")
        for row in reader:
            if len(row) >= 2:
                try:
                    links.append((int(row[0]), int(row[1])))
                except ValueError:
                    pass
    return links


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    print("=" * 50)
    print("Tatoeba インドネシア語↔日本語ペア取得")
    print("=" * 50)

    # ダウンロード
    print("\nステップ1: データをダウンロード中...")
    ind_path   = download("ind_sentences.tsv.bz2", URLS["ind"])
    jpn_path   = download("jpn_sentences.tsv.bz2", URLS["jpn"])
    links_path = download("links.tar.bz2",          URLS["links"])

    # 読み込み
    print("\nステップ2: インドネシア語文を読み込み中...")
    ind_sentences = load_sentences_bz2(ind_path)
    print(f"  {len(ind_sentences):,} 文")

    print("ステップ3: 日本語文を読み込み中...")
    jpn_sentences = load_sentences_bz2(jpn_path)
    print(f"  {len(jpn_sentences):,} 文")

    print("ステップ4: 翻訳リンクを読み込み中（時間がかかります）...")
    links = load_links(links_path)
    print(f"  {len(links):,} ペア")

    # インドネシア語↔日本語ペアを抽出
    print("\nステップ5: インドネシア語↔日本語ペアを抽出中...")
    pairs = []
    ind_set = set(ind_sentences.keys())
    jpn_set = set(jpn_sentences.keys())

    for id1, id2 in links:
        ind_id = jpn_id = None
        if id1 in ind_set and id2 in jpn_set:
            ind_id, jpn_id = id1, id2
        elif id2 in ind_set and id1 in jpn_set:
            ind_id, jpn_id = id2, id1

        if ind_id is None:
            continue

        ind_text = ind_sentences[ind_id]
        jpn_text = jpn_sentences[jpn_id]

        # 長さフィルター
        if not (MIN_LEN <= len(ind_text) <= MAX_LEN):
            continue

        pairs.append({
            "ind_id":  ind_id,
            "jpn_id":  jpn_id,
            "ind":     ind_text,
            "jpn":     jpn_text,
            "ind_url": f"https://tatoeba.org/sentences/show/{ind_id}",
            "jpn_url": f"https://tatoeba.org/sentences/show/{jpn_id}",
        })

        if len(pairs) >= MAX_PAIRS:
            break

    print(f"  {len(pairs)} ペアを抽出しました")

    # 保存
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)

    print(f"\n完了: {OUT_PATH} に保存しました")
    print("=" * 50)


if __name__ == "__main__":
    main()
