# Hermit Audit Checklist — 8축 25항목

**기준일**: 2026-04-18
**버전**: D-minimal v1

각 항목의 레벨 정의:
- **L1**: 기본 인프라 (없으면 FAIL, 있으면 최소 조건 충족)
- **L2**: 동작 품질 (있지만 잘 쓰고 있는지)
- **L3**: 성숙도/최적화 (2026 best-practice 수준)

판정 기준:
- **PASS**: 기준치 충족
- **WEAK_PASS**: 부분 충족 (개선 권장)
- **FAIL**: 기준치 미달 또는 항목 없음
- **N/A**: 해당 환경에서 적용 불가

---

## 축 1 — 구조 (Structure) [3항목]

*check-harness 6축에서 상속. CC 하네스 기반 구조 점검.*

| ID | 항목 | 측정 방법 | PASS 기준 | FAIL 기준 | Level |
|----|------|-----------|-----------|-----------|-------|
| S1 | CLAUDE.md 존재 (User + Project) | `ls ~/.claude/CLAUDE.md && ls CLAUDE.md` | 둘 다 존재 | 하나라도 없음 | L1 |
| S2 | settings.json hooks 설정 | `cat ~/.claude/settings.json \| grep hooks` | hooks 섹션 존재, PostToolUse 최소 1개 | hooks 없음 | L1 |
| S3 | .claude/rules/ 디렉토리 구조 | `ls ~/.claude/rules/*.md` | 최소 2개 rules 파일 존재 | rules 파일 없음 | L1 |

---

## 축 2 — 맥락 (Context) [3항목]

*CLAUDE.md 및 rules 파일의 품질과 로드 메커니즘 점검.*

| ID | 항목 | 측정 방법 | PASS 기준 | FAIL 기준 | Level |
|----|------|-----------|-----------|-----------|-------|
| C1 | CLAUDE.md 간결성 (User) | `wc -w ~/.claude/CLAUDE.md` | ≤ 400 words (~520 tokens) | > 700 words (>910 tokens) | L2 |
| C2 | CLAUDE.md 간결성 (Project) | `wc -w CLAUDE.md` | ≤ 400 words | > 700 words | L2 |
| C3 | rules 파일 총 토큰 합계 | `cat ~/.claude/rules/*.md \| wc -w` (×1.3) | ≤ 4,000 tokens 합계 | > 8,000 tokens | L2 |

---

## 축 3 — 계획 (Plan) [2항목]

*작업 전 계획 습관 점검.*

| ID | 항목 | 측정 방법 | PASS 기준 | FAIL 기준 | Level |
|----|------|-----------|-----------|-----------|-------|
| P1 | /ralplan 또는 /deep-interview 사용 흔적 | session log 키워드 검색: `ralplan\|deep-interview` | 최근 5세션 중 2회 이상 | 0회 | L2 |
| P2 | .omc/plans/ 디렉토리 존재 및 plan 파일 유무 | `ls .omc/plans/*.md 2>/dev/null` | plan 파일 1개 이상 | 디렉토리 없음 | L2 |

---

## 축 4 — 실행 (Execution) [3항목]

*실제 작업 실행 품질 점검.*

| ID | 항목 | 측정 방법 | PASS 기준 | FAIL 기준 | Level |
|----|------|-----------|-----------|-----------|-------|
| E1 | MCP 서버 수 제한 | `settings.json mcpServers` 카운트 | ≤ 5개 | > 8개 | L2 |
| E2 | deny rules 설정 (민감 파일 보호) | `settings.json permissions.deny` | .env, *.key, *.pem deny 존재 | deny 설정 없음 | L1 |
| E3 | PostToolUse formatter hook 존재 | `settings.json hooks.PostToolUse` | 최소 1개 PostToolUse hook | PostToolUse 없음 | L2 |

---

## 축 5 — 검증 (Verification) [2항목]

*작업 완료 전 검증 습관 점검.*

| ID | 항목 | 측정 방법 | PASS 기준 | FAIL 기준 | Level |
|----|------|-----------|-----------|-----------|-------|
| V1 | pytest 실행 흔적 (세션 로그) | session log: `pytest` 키워드 | 최근 코딩 세션에서 pytest 실행 확인 | pytest 미실행 | L2 |
| V2 | /session-wrap 또는 /wrap 사용 습관 | session log: `session-wrap\|/wrap` | 최근 5세션 중 3회 이상 | 0회 | L2 |

---

## 축 6 — 개선 (Improvement) [2항목]

*학습과 개선 루프 점검.*

| ID | 항목 | 측정 방법 | PASS 기준 | FAIL 기준 | Level |
|----|------|-----------|-----------|-----------|-------|
| I1 | Learned feedback skill 존재 | `ls ~/.claude/skills/learned-feedback/ 2>/dev/null` | 1개 이상 learned skill | 없음 | L3 |
| I2 | .omc/notepad.md 또는 project-memory.json 활용 | 파일 존재 + 최근 수정일 | 파일 존재, 30일 이내 수정 | 없음 또는 90일 이상 방치 | L3 |

---

## 축 7 — Token Economy [6항목] ★ 신규

*Hermit 전용. CC 환경에서는 T1/T4만 적용 가능.*

| ID | 항목 | 측정 방법 | PASS 기준 | WEAK_PASS | FAIL 기준 | Level |
|----|------|-----------|-----------|-----------|-----------|-------|
| T1 | Cache hit rate ≥ 80% | Gateway DB: `SELECT AVG(cache_hit) FROM usage` 또는 CC jsonl usage 필드 분석 | ≥ 80% | 60-79% | < 60% | L3 |
| T2 | CLAUDE.md ≤ 500 tokens (User) | `python3 -c "print(int($(wc -w < ~/.claude/CLAUDE.md) * 1.3))"` | ≤ 500 tokens | 501-800 | > 800 tokens | L2 |
| T3 | Memory files 합계 ≤ 4k tokens | `cat ~/.claude/rules/*.md ~/.claude/CLAUDE.md \| wc -w` × 1.3 | ≤ 4,000 tokens | 4,001-6,000 | > 6,000 tokens | L2 |
| T4 | Hermit MCP result 평균 길이 < 2,000자 | Gateway usage 로그 샘플링: `result` 필드 len 평균 | < 2,000자 | 2,000-4,000자 | > 4,000자 | L2 |
| T5 | MCP 서버 수 ≤ 5, 각 스키마 ≤ 2k 토큰 | `settings.json mcpServers` 카운트 | ≤ 5개 | 6-7개 | > 8개 | L2 |
| T6 | Skill body `## Phase N:` 헤더 채택률 | `grep -rl "## Phase" ~/.claude/skills/ \| wc -l` / 전체 SKILL.md 수 | ≥ 50% | 20-49% | < 20% | L3 |

**T1 측정 상세**:
```bash
# CC jsonl 방식 (CC 환경)
cat ~/.claude/projects/*/conversations/*.jsonl 2>/dev/null | \
  python3 -c "
import sys, json
hits, total = 0, 0
for line in sys.stdin:
    try:
        d = json.loads(line)
        u = d.get('usage', {})
        if 'cache_read_input_tokens' in u:
            total += u.get('input_tokens', 0)
            hits += u.get('cache_read_input_tokens', 0)
    except: pass
print(f'Cache hit rate: {hits/total*100:.1f}%' if total else 'No data')
"

# Gateway DB 방식 (Hermit 환경)
sqlite3 ~/.hermit/gateway.db "
  SELECT
    ROUND(AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) * 100, 1) as hit_rate_pct,
    COUNT(*) as total_calls
  FROM usage
  WHERE created_at > datetime('now', '-7 days');
" 2>/dev/null || echo "Gateway DB not available"
```

**T3 측정 상세**:
```bash
# 전체 memory files 토큰 추정
total_words=0
for f in ~/.claude/CLAUDE.md ~/.claude/rules/*.md; do
  [ -f "$f" ] || continue
  words=$(wc -w < "$f")
  total_words=$((total_words + words))
  echo "  $f: ~$(python3 -c "print(int($words * 1.3))") tokens"
done
echo "합계: ~$(python3 -c "print(int($total_words * 1.3))") tokens (목표: ≤ 4,000)"
```

---

## 축 8 — Model Routing [4항목] ★ 신규

*Hermit Gateway 전용. CC 단독 환경에서는 N/A.*

| ID | 항목 | 측정 방법 | PASS 기준 | WEAK_PASS | FAIL 기준 | Level |
|----|------|-----------|-----------|-----------|-----------|-------|
| M1 | Gateway 모델별 실패율 < 5% | `usage.status='error'` 비율 by model | < 5% | 5-15% | > 15% | L2 |
| M2 | Fallback 빈도 (모델 전환) | `model_changed` 이벤트 카운트 / 전체 calls | < 10% | 10-25% | > 25% | L2 |
| M3 | 로컬 vs 클라우드 분산 의도적 설계 | `usage.model` 분포 확인 + config 검토 | 분산 정책이 config에 명시됨 | 분산되나 정책 없음 | 단일 모델 의존 | L3 |
| M4 | 긴 태스크 Monitor 사용 여부 | session log: `Monitor\|run_in_background` 패턴 vs `sleep` | Monitor/background 패턴 우세 | 혼용 | sleep 루프만 사용 | L2 |

**M1 측정 상세**:
```bash
sqlite3 ~/.hermit/gateway.db "
  SELECT
    model,
    COUNT(*) as total,
    SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
    ROUND(100.0 * SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) / COUNT(*), 1) as error_pct
  FROM usage
  WHERE created_at > datetime('now', '-7 days')
  GROUP BY model
  ORDER BY total DESC;
" 2>/dev/null || echo "Gateway DB unavailable"
```

**M3 측정 상세**:
```bash
sqlite3 ~/.hermit/gateway.db "
  SELECT model, COUNT(*) as calls
  FROM usage
  WHERE created_at > datetime('now', '-7 days')
  GROUP BY model
  ORDER BY calls DESC;
" 2>/dev/null || echo "Gateway DB unavailable"
```

---

## 2026 기법 필수 8개 자동체크 (Quick Scan)

감사 시작 시 30초 내로 실행 가능한 빠른 상태 확인:

| # | 항목 | 빠른 명령 | 연결 축 |
|---|------|-----------|---------|
| Q1 | Cache hit rate | T1 측정 명령 참조 | T1 |
| Q2 | MCP server count | `python3 -c "import json; s=json.load(open(os.path.expanduser('~/.claude/settings.json'))); print(len(s.get('mcpServers', {})))"` | T5, E1 |
| Q3 | Deny rules 존재 | `grep -c "deny" ~/.claude/settings.json` | E2 |
| Q4 | PostToolUse hook | `grep -c "PostToolUse" ~/.claude/settings.json` | E3 |
| Q5 | Monitor 사용 패턴 | `grep -r "run_in_background\|Monitor" ~/.hermit/sessions/ 2>/dev/null \| wc -l` | M4 |
| Q6 | CLAUDE.md size | `wc -w ~/.claude/CLAUDE.md` | T2, C1 |
| Q7 | Rules 합계 토큰 | T3 측정 명령 참조 | T3, C3 |
| Q8 | Skill phased 채택률 | `grep -rl "## Phase" ~/.claude/skills/ 2>/dev/null \| wc -l` | T6 |

---

## 스코어카드 템플릿

감사 완료 후 아래 형식으로 기록:

```markdown
## Scorecard — YYYY-MM-DD

| 축 | 이름 | 점수 | 레벨 | 비고 |
|----|------|------|------|------|
| 1 | 구조 | PASS | L1 | |
| 2 | 맥락 | WEAK_PASS | L2 | CLAUDE.md 620 tokens > 500 목표 |
| 3 | 계획 | PASS | L2 | |
| 4 | 실행 | PASS | L2 | |
| 5 | 검증 | WEAK_PASS | L2 | session-wrap 습관 부족 |
| 6 | 개선 | PASS | L3 | |
| 7 | Token Economy | WEAK_PASS | L2 | T3: 5,200 tokens > 4,000 목표 |
| 8 | Model Routing | N/A | — | Gateway DB 미설정 |

**종합 레벨**: L2 (3개 WEAK_PASS, 1개 N/A)

**Quick Wins**:
1. CLAUDE.md 다이어트: verbose 예시 제거 → -200 tokens
2. rules 파일 합계: feedback-learning.md 스킬화 → -730 tokens
3. session-wrap 습관: 세션 종료 전 /session-wrap 루틴화

**Post-optimization target**: memory files sum ≤ 3,000 tokens
```
