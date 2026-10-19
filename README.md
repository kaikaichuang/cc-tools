# cc-tools

給 Claude Code 用的小工具。不需要 sudo，只用 Python 3 內建套件。

## ccs：管理 Claude Code session

用一個選單進入 session，不用自己判斷該用 `claude -r` 還是 `claude attach`；也能把用不到的 session 封存起來。被封存的 session 不會出現在 `/resume` 清單裡，但不會被刪除，隨時可以還原。封存的檔案放在 `~/.local/share/ccs/`（可以用 `CCS_DIR` 改位置）。

舊名稱 `cc-archive` 目前還能用，它直接指向 `ccs`。

### 在終端機使用

```bash
ccs                 # 互動選單（列出目前資料夾的 session）
ccs ID...           # 封存，ID 打前幾碼就可以
ccs -l              # 列出已封存的 session
ccs -r ID...        # 還原，或取消「關閉後封存」
ccs --restore-all   # 還原所有專案的所有已封存 session
ccs --update        # 更新到最新版（git pull，再執行 install.sh）
ccs --uninstall     # 解除安裝（見下方）
ccs -p DIR ...      # 對別的專案資料夾操作
ccs -f ID           # 無法判斷 session 是否還開著時，確定沒在用才強制封存
```

選單操作：上下鍵選擇、`Ctrl+A` 封存／還原（再按一次就復原）、`Enter` 進入該 session、`q` 離開。

按 `Enter` 時會自動選擇不會產生副本的進入方式：

| session 的狀態 | Enter 會執行 |
|---|---|
| 正在背景跑 | `claude attach <id>` |
| 在另一個 claude 視窗開著 | 不進入，提示你切到那個視窗 |
| 沒有在跑 | `claude --resume <id>` |

| 標記 | 意思 |
|---|---|
| `[A]` | 已封存 |
| `[P]` | 該 session 還開著，關閉後會自動封存 |
| ` * ` | 正在某個 claude 裡開著 |

還開著的 session 不能直接搬移，因為 Claude 還在寫入它。這種 session 會先被標成 `[P]`，等那個 claude 關掉之後，在下一次啟動 claude 或執行 `ccs` 時才封存。不會留下任何背景程式。

判斷 session 是否還開著，靠的是 Claude 的 `~/.claude/sessions/<pid>.json` 紀錄，另外要求檔案至少 10 秒沒有寫入。

如果這份紀錄不存在、格式看不懂，或重讀幾次仍讀不到（Claude 隨時在改寫它），ccs 就當作「無法判斷」，什麼都不會自動搬。手動封存時它會停下來提醒你；你確定沒有 claude 在用那個 session，才用 `ccs -f ID` 強制封存。檔案很久沒寫入，不代表 claude 已經關掉，所以不會拿這點來判斷。

搬移是「全有或全無」：一個 session 的檔案只要有一個搬失敗，已經搬過去的會全部搬回原處，不會拆成兩半。

### 自動清掉 Claude 產生的對話副本

如果離開 Claude 時還有 agent 在背景跑（例如按兩次 Ctrl+C），Claude Code 會把對話交給一個新的背景 session 繼續，於是 `/resume` 裡會多出一份同樣標題的副本，例如「(2)」。

ccs 每次執行時（外掛會在每次啟動 Claude 時也跑一次），會把這些副本封存起來，同一段對話只留下最完整的那一份：訊息最多的那份，一樣多時留最新的那份。所以就算你不小心在副本裡繼續聊，留下的也會是那一份。

- 只處理 Claude 自動產生的副本，這種副本的原檔裡會有一筆 `continued-in` 紀錄。你用 `/branch`、`--fork-session` 刻意開的分支不會被動到。
- 還開著的副本不會被動。
- 被封存的副本可以用 `ccs -r ID` 還原。手動還原過的 session，之後不會再被自動封存。

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
/plugin install ccs --marketplace kaikaichuang/cc-tools
```

如果 repo 是私人的，該機器要先有 GitHub 的存取權限（SSH key 或 token）。

## 解除安裝

```bash
ccs --uninstall
```

會依序：

1. 把所有已封存的 session 搬回 Claude 原本的資料夾，`/resume` 又看得到它們。
2. 取消所有「關閉後封存」的標記。
3. 移除 ccs 外掛和 `cc-tools` marketplace。
4. 移除 `~/.local/bin` 裡指向 cc-tools 的指令。
5. 刪掉 ccs 的資料夾。只刪 ccs 自己建的東西，有其他檔案就留著並告訴你。

任何一個 session 搬不回去，就會在刪除任何東西之前停下來。cc-tools 的程式碼本身不會被刪，完成後會印出刪除它的指令。

## 從 cc-archive 升級

```bash
cc-archive --update                       # 舊版的 --update 只會 git pull
~/.local/share/cc-tools/install.sh        # 建立 ccs 指令，並把封存資料搬到 ~/.local/share/ccs
claude plugin uninstall cc-archive@cc-tools && claude plugin install ccs@cc-tools   # 有裝外掛才需要
```

## 更新

```bash
ccs --update                                          # CLI
claude plugin update ccs@cc-tools                     # 外掛，之後在 Claude 裡執行 /reload-plugins
```

## 開發

```bash
python3 -m unittest discover -s tests                 # CLI 測試（用假的 HOME，不會碰到真的 session）
claude plugin validate plugins/ccs
(cd plugins/ccs && claude plugin test .)              # 外掛測試
```

`ccs` 讀的是 Claude Code 沒有公開的內部格式：

- `~/.claude/projects/<專案>/<id>.jsonl`
- 標題紀錄：`custom-title` 優先於 `ai-title`
- `~/.claude/sessions/<pid>.json`：記錄哪些 session 正開著

Claude Code 改版後如果出問題，先跑一次測試；確定是格式變了，就照新格式修好再 push，其他機器 `--update` 就會拿到修正。

如果 Claude Code 之後內建了封存功能，執行 `ccs --restore-all` 把所有 session 還原，再停用這個工具即可。

另外，Claude Code 的 `cleanupPeriodDays` 設定（預設 30 天）會自動刪除太久沒動的 session。想長期保留的話，可以把這個值調大。ccs 封存的 session 不在 `~/.claude` 裡，不會被這個設定刪掉；還原時會把檔案時間更新成現在，避免一還原就被清掉。
