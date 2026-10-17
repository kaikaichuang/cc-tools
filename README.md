# cc-tools

給 Claude Code 用的小工具。不需要 sudo，只用 Python 3 內建套件。

## cc-archive：封存 session

被封存的 session 不會出現在 `/resume` 清單裡，但不會被刪除，隨時可以還原。封存的檔案放在 `~/.local/share/cc-archive/`（可以用 `CC_ARCHIVE_DIR` 改位置）。

### 在終端機使用

```bash
cc-archive                 # 互動選單（列出目前資料夾的 session）
cc-archive ID...           # 封存，ID 打前幾碼就可以
cc-archive -l              # 列出已封存的 session
cc-archive -r ID...        # 還原，或取消「關閉後封存」
cc-archive --restore-all   # 還原所有專案的所有已封存 session
cc-archive --update        # 更新到最新版（git pull）
cc-archive -p DIR ...      # 對別的專案資料夾操作
```

選單操作：上下鍵選擇、`Ctrl+A` 封存／還原（再按一次就復原）、`Enter` 接續該 session、`q` 離開。

| 標記 | 意思 |
|---|---|
| `[A]` | 已封存 |
| `[P]` | 該 session 還開著，關閉後會自動封存 |
| ` * ` | 正在某個 claude 裡開著 |

還開著的 session 不能直接搬移，因為 Claude 還在寫入它。這種 session 會先被標成 `[P]`，等那個 claude 關掉之後，在下一次啟動 claude 或執行 `cc-archive` 時才封存。不會留下任何背景程式。

判斷 session 是否還開著，靠的是 Claude 的 `~/.claude/sessions/<pid>.json` 紀錄，另外要求檔案至少 10 秒沒有寫入。如果這份紀錄的格式變了、讀不懂，就改用保守規則：2 分鐘內有寫入的 session 一律當作還開著。

### 在 Claude 裡使用（外掛）

```
/archive              這個 session 關閉後封存（/unarchive 取消）
/archive ID           立刻封存另一個 session
/archive list         列出這個專案的 session
/unarchive ID         還原
/unarchive list       列出已封存的 session
```

## 安裝（新機器，不需要 sudo）

```bash
git clone https://github.com/kaikaichuang/cc-tools ~/.local/share/cc-tools
~/.local/share/cc-tools/install.sh
```

`install.sh` 會把 `bin/` 裡的工具連結到 `~/.local/bin`。如果 `~/.local/bin` 不在 PATH 裡，它會告訴你要加哪一行。

外掛（選用）：在 Claude 裡輸入

```
/plugin install cc-archive --marketplace kaikaichuang/cc-tools
```

如果 repo 是私人的，該機器要先有 GitHub 的存取權限（SSH key 或 token）。

## 更新

```bash
cc-archive --update                                   # CLI
claude plugin update cc-archive@cc-tools              # 外掛，之後在 Claude 裡執行 /reload-plugins
```

## 開發

```bash
python3 -m unittest discover -s tests                 # CLI 測試（用假的 HOME，不會碰到真的 session）
claude plugin validate plugins/cc-archive
(cd plugins/cc-archive && claude plugin test .)       # 外掛測試
```

`cc-archive` 讀的是 Claude Code 沒有公開的內部格式：

- `~/.claude/projects/<專案>/<id>.jsonl`
- 標題紀錄：`custom-title` 優先於 `ai-title`
- `~/.claude/sessions/<pid>.json`：記錄哪些 session 正開著

Claude Code 改版後如果出問題，先跑一次測試；確定是格式變了，就照新格式修好再 push，其他機器 `--update` 就會拿到修正。

如果 Claude Code 之後內建了封存功能，執行 `cc-archive --restore-all` 把所有 session 還原，再停用這個工具即可。

另外，Claude Code 的 `cleanupPeriodDays` 設定（預設 30 天）會自動刪除太久沒動的 session。想長期保留的話，可以把這個值調大。cc-archive 封存的 session 不在 `~/.claude` 裡，不會被這個設定刪掉；還原時會把檔案時間更新成現在，避免一還原就被清掉。
