# midi-ball
 
技術経営論文付随プログラム
 
# Features

midiデバイス2本で画面上のボールを操作
 
# Requirement
  
* kivy  2.2.1
* python-rtmidi 1.5.5
* rtmidi  2.5.0
* sqlite  3
 
# Installation
  
```bash
pip install kivy
pip install python-rtmidi
pip install pysqlite3
```
 
# Usage

parameters.txtを編集

```bash
git clone https://github.com/rtoki/midi-ball
cd midi-ball
python midi-ball.py
```
 
# Note
 
MBP M2 Mac 上でElefue 2本にて動作確認

event.dbが作成される
DB構造
* games
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            current_map_index INTEGER,
            end_time TEXT,
            score INTEGER,
            score_player1 INTEGER DEFAULT 0,
            score_player2 INTEGER DEFAULT 0,
            restart_count INTEGER,
            elapsed_time FLOAT
        )
* events        
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            time TEXT,
            x_position INTEGER,
            y_position INTEGER,
            difference INTEGER, 
            is_overlapping BOOLEAN DEFAULT 0, 
            velocity_player1 INTEGER,
            pitch_player1 INTEGER,
            velocity_player2 INTEGER,
            pitch_player2 INTEGER,
            FOREIGN KEY (game_id) REFERENCES games (id)
        )

# Author
  
* rtoki
