from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable
import math

import numpy as np
from PIL import Image, ImageFilter


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _load_embedding(path: str | Path, preview_size: int = 32) -> np.ndarray:
    img = Image.open(path).convert('RGB')
    img = img.resize((preview_size, preview_size))
    gray = img.convert('L')
    edges = gray.filter(ImageFilter.FIND_EDGES)
    rgb = np.asarray(img, dtype=np.float32) / 255.0
    gray_arr = np.asarray(gray, dtype=np.float32) / 255.0
    edge_arr = np.asarray(edges, dtype=np.float32) / 255.0
    feat = np.concatenate([
        rgb.mean(axis=(0, 1)),
        rgb.std(axis=(0, 1)),
        gray_arr.reshape(-1),
        edge_arr.reshape(-1),
    ])
    norm = float(np.linalg.norm(feat))
    return feat if norm <= 1e-12 else (feat / norm)


def _pairwise_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - np.dot(a, b))


def cluster_series(paths: Iterable[str | Path], cluster_eps: float = 0.18, min_samples: int = 2, preview_size: int = 32) -> tuple[list[int], list[np.ndarray | None]]:
    path_list = [Path(p) for p in paths]
    embeddings: list[np.ndarray | None] = []
    for path in path_list:
        try:
            embeddings.append(_load_embedding(path, preview_size=preview_size))
        except Exception:
            embeddings.append(None)
    labels = [-1] * len(path_list)
    parent = list(range(len(path_list)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(path_list)):
        if embeddings[i] is None:
            continue
        for j in range(i + 1, len(path_list)):
            if embeddings[j] is None:
                continue
            if _pairwise_distance(embeddings[i], embeddings[j]) <= float(cluster_eps):
                union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for idx in range(len(path_list)):
        if embeddings[idx] is None:
            continue
        groups[find(idx)].append(idx)

    next_label = 0
    for idxs in groups.values():
        if len(idxs) < int(min_samples):
            continue
        for idx in idxs:
            labels[idx] = next_label
        next_label += 1
    return labels, embeddings


def _rating_for_score(final_score: float, cfg: dict) -> int:
    bands = cfg.get('culling', {}).get('star_rating_bands', {5: 0.90, 4: 0.75, 3: 0.60, 2: 0.40, 1: 0.20, 0: 0.00})
    normalized = []
    for stars, min_score in bands.items():
        try:
            normalized.append((int(stars), float(min_score)))
        except Exception:
            continue
    if not normalized:
        normalized = [(5, 0.90), (4, 0.75), (3, 0.60), (2, 0.40), (1, 0.20), (0, 0.00)]
    score = max(0.0, min(1.0, float(final_score)))
    for stars, min_score in sorted(normalized, key=lambda x: (-x[1], -x[0])):
        if score >= min_score:
            return stars
    return 0


def _decision_rank(decision: str) -> int:
    return {'reject': 0, 'review': 1, 'keep': 2}.get(str(decision).strip().lower(), 1)


def _decision_name(rank: int) -> str:
    return {0: 'reject', 1: 'review', 2: 'keep'}.get(max(0, min(2, int(rank))), 'review')


def _promote_one(decision: str) -> str:
    return _decision_name(_decision_rank(decision) + 1)


def _demote_one(decision: str) -> str:
    return _decision_name(_decision_rank(decision) - 1)

def apply_series_culling(rows: list[dict], cfg: dict) -> list[dict]:
    series_cfg = cfg.get('series_detection', {})
    enabled = bool(series_cfg.get('enabled', True)) and len(rows) > 1
    if not enabled:
        for row in rows:
            row['score_decision'] = row.get('score_decision', row.get('decision', 'review'))
            row['series_id'] = 'single'
            row['series_size'] = 1
            row['series_rank'] = 1
            row['series_best'] = True
            row['series_margin_to_best'] = 0.0
            row['decision'] = row['score_decision']
            row['decision_reason'] = row.get('score_reason', 'score_threshold')
            row['star_rating'] = _rating_for_score(float(row.get('final_score', 0.0)), cfg)
        return rows

    labels, _ = cluster_series(
        [row['_source_path'] for row in rows],
        cluster_eps=float(series_cfg.get('cluster_eps', 0.18)),
        min_samples=int(series_cfg.get('min_samples', 2)),
        preview_size=int(series_cfg.get('preview_size', 32)),
    )
    for row, label in zip(rows, labels):
        row['_series_label'] = label
        row['score_decision'] = row.get('score_decision', row.get('decision', 'review'))

    grouped: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[int(row['_series_label'])].append(row)

    review_margin = float(series_cfg.get('review_margin', 0.03))
    demote_non_best_to = str(series_cfg.get('demote_non_best_to', 'review')).strip().lower()
    for label, items in grouped.items():
        if label == -1:
            for item in items:
                item['series_id'] = 'single'
                item['series_size'] = 1
                item['series_rank'] = 1
                item['series_best'] = True
                item['series_margin_to_best'] = 0.0
                item['decision'] = item['score_decision']
                item['decision_reason'] = item.get('score_reason', 'score_threshold')
                item['star_rating'] = _rating_for_score(float(item.get('final_score', 0.0)), cfg)
            continue

        ranked = sorted(items, key=lambda x: (-float(x['final_score']), x['file']))
        best_score = float(ranked[0]['final_score'])
        for pos, item in enumerate(ranked, start=1):
            margin = round(best_score - float(item['final_score']), 4)
            item['series_id'] = f'series_{label}'
            item['series_size'] = len(ranked)
            item['series_rank'] = pos
            item['series_best'] = pos == 1
            item['series_margin_to_best'] = margin
            base_decision = str(item.get('score_decision', item.get('decision', 'review'))).strip().lower()

            if pos == 1:
                if base_decision == 'keep':
                    final_decision = 'keep'
                    reason = 'series_best_confirmed'
                elif base_decision == 'review':
                    final_decision = 'keep'
                    reason = 'series_best_promoted'
                else:
                    final_decision = 'review'
                    reason = 'series_best_salvaged'
            elif margin <= review_margin:
                final_decision = 'review'
                reason = 'series_near_best'
            else:
                if demote_non_best_to == 'reject':
                    final_decision = _demote_one(base_decision)
                    reason = 'series_demoted_hard'
                else:
                    final_decision = 'review' if base_decision == 'keep' else base_decision
                    reason = 'series_demoted_soft' if base_decision == 'keep' else item.get('score_reason', 'score_threshold')

            if item.get('protected_by_family_rule') and final_decision == 'reject':
                final_decision = 'review'
                reason = 'family_protected_series'

            item['decision'] = final_decision
            item['decision_reason'] = reason
            item['star_rating'] = _rating_for_score(float(item.get('final_score', 0.0)), cfg)

    for row in rows:
        row.pop('_series_label', None)
    return rows
