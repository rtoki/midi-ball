#-*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.properties import StringProperty

import rtmidi

from map_loader import MapLoader

import os
import shutil

# 定数
WINDOW_SIZE = (800, 800)
BALL_RADIUS = 40
TIME_LIMIT = 15
UPDATE_INTERVAL = 1/60
MIDI_MAX_VELOCITY = 127
VELOCITY_CONVERSION_FACTOR = 6

Window.size = WINDOW_SIZE  # ウィンドウサイズを設定


# ボールクラス
class Ball(Widget):
    def __init__(self, **kwargs):
        super(Ball, self).__init__(**kwargs)
        with self.canvas:
            Color(1, 1, 1, 1) 
            self.rect = Rectangle(source='data/ball.png', pos=self.pos, size=(80, 80))
        self.speed_right = 0
        self.speed_up = 0
        self.accelerate_right = False
        self.accelerate_up = False
        self.decelerate_right = False
        self.decelerate_up = False
        self.last_midi_device = 0
        self.velocity_factor_right = 0.0
        self.velocity_factor_up = 0.0


    def update(self):
        # Handle acceleration and deceleration
        if self.accelerate_right:
            self.speed_right = min(0.85, self.speed_right + 0.015 * self.velocity_factor_right)
        if self.decelerate_right:
            self.speed_right = max(0, self.speed_right - 0.01)
        if self.accelerate_up:
            self.speed_up = min(0.85, self.speed_up + 0.015 * self.velocity_factor_up)
        if self.decelerate_up:
            self.speed_up = max(0, self.speed_up - 0.01)

        # Update ball position
        x, y = self.rect.pos
        x += self.speed_right
        y += self.speed_up
        x = max(0, min(WINDOW_SIZE[0] - self.rect.size[0], x))
        y = max(0, min(WINDOW_SIZE[1] - self.rect.size[1], y))
        self.rect.pos = (x, y)


# ゴールのクラス
class Goal(Widget):
    def __init__(self, **kwargs):
        super(Goal, self).__init__(**kwargs)
        with self.canvas:
            Color(1, 1, 1, 1) 
            self.rect = Rectangle(source='data/goal.png', pos=self.pos, size=(80, 80))
        # ゴールの初期位置を右上に移動
        self.rect.pos = (WINDOW_SIZE[0] - 80, WINDOW_SIZE[1] - 80)


class BallMap(Widget):
    map_image_source = StringProperty('data/default_image.png')
    def __init__(self, **kwargs):
        super(BallMap, self).__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            
        #self.image.pos = (0, 0)
        #self.image.size = (800, 800)

# ゲームのメインウィジェット
class GameScreen(Widget):
    block_size = 1 # ブロックのサイズ (80x80の場合は10)

    def __init__(self, conn, midi_inputs, params, **kwargs):
        super(GameScreen, self).__init__(**kwargs)
        # 各プレイヤーの得点を初期化
        self.scores = [0, 0]  # [Player 1 score, Player 2 score]
        self.last_moved_by = None  # 最後にボールを動かしたプレイヤーを記録        

        self.last_midi_velocity = [0, 0]
        self.last_midi_pitch = [0, 0]

        self.time_label = Label(text='Time: 0', pos=(10, 680), font_size='12sp')  # 経過時間のラベル
        self.add_widget(self.time_label)

        self.conn = conn
        self.cursor = conn.cursor() # cursorをインスタンス変数に設定
        self.midi_inputs = midi_inputs # midi_inputsをインスタンス変数に設定
        self.time_limit = TIME_LIMIT  # 15秒のタイムリミット
        self.is_game_started = False  # ゲームが開始しているかどうかを追跡する変数
        self.elapsed_time = 0  # タイムリミットに達したかどうかを追跡する変数
        self.ball = self.ids.ball
        self.goal = self.ids.goal
        self.positions = []  # ボールの位置を保存するリスト
        self.goal_label = None  # goal_label を初期化
        self.restart_count = 0  # 再起動回数のカウント用

        self.last_overlap = False  # 最後に重なっていたかどうかを記録

        # カウントダウンラベルの追加
        self.countdown_label = Label(font_size='30sp', pos=(WINDOW_SIZE[0]/2 - 50, WINDOW_SIZE[1]/2 - 50), color=[0, 0, 0, 1])
        self.add_widget(self.countdown_label)
        self.countdown_seconds = 5

        # キーボード入力の設定
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self._keyboard.bind(on_key_up=self._on_key_up)

        self.params = params
        self.current_map_index = 1
        self.load_map()

        self.overlap_count = 0  # 重なりの回数をカウントするための変数を追加

    def load_map(self):
        map_data_key = f"map_data{self.current_map_index}"
        map_image_key = f"map_image{self.current_map_index}"
        self.map_data = MapLoader.load_map(self.params[map_data_key])
        self.map_image = Image(source=self.params[map_image_key])
        self.ids.ballMap.map_image_source = self.params[map_image_key]
        


    # ボールとブロックが重なっているかどうかをチェック
    def check_overlap(self, ball_pos):
        # ボールの中心座標を計算
        ball_center = (ball_pos[0] + BALL_RADIUS, ball_pos[1] + BALL_RADIUS)
        

        # ボールの範囲内に含まれるブロックの範囲を計算
        min_row = max(0, int((ball_center[1] - BALL_RADIUS/5) / self.block_size))
        max_row = min(len(self.map_data) - 1, int((ball_center[1] + BALL_RADIUS/5) / self.block_size))
        min_col = max(0, int((ball_center[0] - BALL_RADIUS/5) / self.block_size))
        max_col = min(len(self.map_data[0]) - 1, int((ball_center[0] + BALL_RADIUS/5) / self.block_size))

        # ブロックサイズごとに重なりをチェック
        for row_index in range(min_row, max_row + 1):
            for col_index in range(min_col, max_col + 1):
                val = self.map_data[800 - 1 - row_index][col_index]
                if val > 1:  # 線がある場所のみチェック                    
                    # print(f"Overlap detected! {row_index}, {col_index}, {val}")
                    return val  # 重なりがあればTrueを返す
        return 0  # 重なりがなければFalseを返す
    
    # ゲームをリセット
    def reset_game(self):
        self.elapsed_time = 0
        # ボールの位置と速度をリセット
        self.ball.rect.pos = (0, 0)
        self.ball.speed_right = 0
        self.ball.speed_up = 0
        self.ball.accelerate_right = False
        self.ball.accelerate_up = False
        self.ball.decelerate_right = False
        self.ball.decelerate_up = False
        self.ids.statusLabel.text = "" # ステータスラベルをクリア
        if hasattr(self, "goal_label"):
            self.remove_widget(self.goal_label)
        self.countdown_label.opacity = 0  # ラベルを非表示
        Clock.unschedule(self.update_countdown)  # カウントダウンのスケジューリングを停止
        

    # ゲーム終了処理 (ボールとゴールが重なったとき)
    def end_game(self):
        # ゲーム終了時の処理
        self.is_game_started = False  # ゲームを終了
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        score = self.overlap_count  # スコアを重なりの回数とする

        Clock.unschedule(self.update_screen_handler)  # update メソッドのスケジューリングを停止

        # ゴールラベルを表示
        self.ids.statusLabel.text = f"Game ID: {self.game_id}, Current Map: {self.current_map_index}, Score: {score}, Restart Count: {self.restart_count}, Elapsed Time: {self.elapsed_time}"


        print(self.ids.statusLabel.text)
        try:
            # positionsに保存された位置情報をデータベースにバルク挿入
            insert_query = "INSERT INTO events (game_id, time, x_position, y_position, difference, is_overlapping, velocity_player1, pitch_player1, velocity_player2, pitch_player2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            # 各位置情報にゲームIDを追加
            values = [(self.game_id, *position) for position in self.positions]
            self.cursor.executemany(insert_query, values)

            # gamesテーブルの現在のゲームセッションを更新
            self.cursor.execute("UPDATE games SET current_map_index = ?, end_time = ?, score = ?, score_player1 = ?, score_player2 = ?, restart_count = ?, elapsed_time = ? WHERE id = ?", (self.current_map_index, end_time, score, self.scores[0], self.scores[1], self.restart_count, self.elapsed_time, self.game_id))
            self.cursor.close()
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")

        # カウントダウンの初期化とスタート
        self.countdown_seconds = 15
        self.countdown_label.text = "Get ready for the start in " + str(self.countdown_seconds)
        self.countdown_label.opacity = 1  # ラベルを表示
        Clock.schedule_interval(self.update_countdown, 1)



    def update_countdown(self, dt):
        self.countdown_seconds -= 1
        if self.countdown_seconds <= 0:
            self.countdown_label.opacity = 0  # ラベルを非表示
            Clock.unschedule(self.update_countdown)  # カウントダウンのスケジューリングを停止
            self.startButton_clicked()  # ゲームを再開
        else:
            self.countdown_label.text = str(self.countdown_seconds)


    # Define a helper function to process each MIDI input
    def process_midi_input(self, input_port, index):
        velocity_factor = 0.0
        midi_events = input_port.get_message()
        velocity = 0

        if midi_events:
            midi_event, _ = midi_events
            status = midi_event[0]
            pitch = midi_event[1] if len(midi_event) > 1 else 0
            velocity = midi_event[2] if len(midi_event) > 2 else 0  # Retrieve velocity
            velocity_factor = velocity / MIDI_MAX_VELOCITY * VELOCITY_CONVERSION_FACTOR

            self.last_midi_device = index  # Update the last operated MIDI device
            self.last_midi_velocity[index] = velocity  # Update the last velocity

            # Define MIDI event behaviors
            if status == 128:  # note_off event
                if index == 0:
                    self.ball.decelerate_right = True
                    self.ball.accelerate_right = False
                else:
                    self.ball.decelerate_up = True
                    self.ball.accelerate_up = False
            elif status == 144:  # note_on event
                if index == 0:
                    self.ball.accelerate_right = True
                    self.ball.decelerate_right = False
                else:
                    self.ball.accelerate_up = True
                    self.ball.decelerate_up = False
            elif status == 176:  # Control Change event
                # Define Control Change behavior here
                pass

            # Update the status label
            label_text = f"Device {index+1} - Status: {status}, Pitch: {pitch}, Velocity: {velocity}"
            if index == 0:
                self.ids.statusLabel1.text = label_text
            else:
                self.ids.statusLabel2.text = label_text

            self.last_midi_pitch[index] = pitch  # Update the last pitch

        return velocity_factor

    # 1/60秒ごとにClockで呼び出される
    # ボールの位置を更新
    def update_screen_handler(self, dt):
        if not self.is_game_started:  # ゲームが開始していない場合は更新しない
            return
        
        self.elapsed_time = (datetime.now() - self.start_time).total_seconds()
        self.time_label.text = f'Time: {self.elapsed_time:.2f}'  # 経過時間の更新

        # Process the two MIDI inputs separately
        self.ball.velocity_factor_right = self.process_midi_input(self.midi_inputs[0], 0) if self.midi_inputs else 10.0
        self.ball.velocity_factor_up = self.process_midi_input(self.midi_inputs[1], 1) if self.midi_inputs else 10.0

        # ボールの更新
        self.ball.update()

        x, y = self.ball.rect.pos
        difference = abs(x - y)  # xとyの差の絶対値を計算

        is_overlapping = False
        if self.ball.speed_right > 0.5 or self.ball.speed_up > 0.5:        
            # ボールと赤い線が重なっているかを確認
            val = self.check_overlap(self.ball.rect.pos)
            if val  > 0:
                # print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " Ball is overlapping with the line!")
                is_overlapping = True  # 重なりをチェック
                self.overlap_count += val

         # ピッチとベロシティを取得
        velocity_player1 = self.last_midi_velocity[0]
        velocity_player2 = self.last_midi_velocity[1]
        pitch_player1 = self.last_midi_pitch[0]
        pitch_player2 = self.last_midi_pitch[1]

        self.positions.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), x, y, difference, is_overlapping, velocity_player1, pitch_player1, velocity_player2, pitch_player2))


        # ボールとゴールの衝突チェック
        pos1 = self.ball.rect.pos
        size1 = self.ball.rect.size
        pos2 = self.goal.rect.pos
        size2 = self.goal.rect.size
        if (pos1[0] < pos2[0] + size2[0] and
        pos1[0] + size1[0] > pos2[0] and
        pos1[1] < pos2[1] + size2[1] and
        pos1[1] + size1[1] > pos2[1]):
            self.end_game()  # ゲーム終了処理を呼び出す


    # Game Startボタンが押された
    def startButton_clicked(self):
        self.reset_game()   # ゲームをリセット
        self.is_game_started = True  # ゲームを開始
        self.start_time = datetime.now()  # ゲームの開始時刻
        self.positions.clear()  # 前のゲームの位置データをクリア
        self.scores = [0, 0]  # スコアをリセット
        self.overlap_count = 0  # 重なりの回数をリセット

        # ...
        self.load_map()  # マップをロードする
        # ...

        # ゲームを再開するたびにマップインデックスを更新する
        self.current_map_index += 1
        if self.current_map_index > 3:
            self.current_map_index = 1


        # データベース処理
        try:
            self.cursor = self.conn.cursor()
            self.cursor.execute("INSERT INTO games (end_time, score) VALUES (?, ?)", (None, 0))
            self.game_id = self.cursor.lastrowid  # 新しいゲームセッションのIDを取得
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")

        # update screen メソッドをスケジューリング
        Clock.schedule_interval(self.update_screen_handler, UPDATE_INTERVAL)

    # Restartボタンが押された
    def restartButton_clicked(self):
        self.reset_game()
        self.elapsed_time = 0
        self.restart_count += 1

    # Renew DBボタンが押された
    def renewDBButton_clicked(self):
        # まずはコミット
        self.conn.commit()
        # データベース接続を閉じる
        self.conn.close()

        # 現在の events.db を events_現在時刻.db として保存
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_db_name = f"events_{current_time}.db"
        shutil.copy2('events.db', backup_db_name)

        # events.db ファイルを削除
        os.remove('events.db')
        
        print(f"events.db has been renewed. Backup file: {backup_db_name}")

        # 新しい events.db を作成
        self.conn = sqlite3.connect('events.db')
        self.parent.conn = self.conn    # 親にもセットする
        self.cursor = self.conn.cursor()
        
        # gamesテーブルの作成
        self.cursor.execute('''
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
        ''')
        
        # eventsテーブルの作成
        self.cursor.execute('''
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
        ''')
        self.conn.commit()


    def _on_key_down(self, keyboard, keycode, text, modifiers):
        #print(f"on key down {keycode[1]}")
        if keycode[1] == 'spacebar':
            if not self.is_game_started:
                self.startButton_clicked()
        elif keycode[1] == 'right':
            self.ball.accelerate_right = True
            self.last_moved_by = 0  # Player 1 (右移動)
        elif keycode[1] == 'up':
            self.ball.accelerate_up = True
            self.last_moved_by = 1  # Player 2 (上移動)

    def _on_key_up(self, keyboard, keycode):
        #print(f"on key up {keycode[1]}")
        if keycode[1] == 'right':
            self.ball.decelerate_right = True
            self.ball.accelerate_right = False
        elif keycode[1] == 'up':
            self.ball.decelerate_up = True
            self.ball.accelerate_up = False

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard.unbind(on_key_up=self._on_key_up)
        self._keyboard = None


class MidiballApp(App):
    use_midi = 0
    conn = None
    midi_inputs = []
    map_data = None
    map_image = None

    # ウィンドウが開かれたときに呼び出される
    def build(self):
        # ウィンドウの背景色を白に設定
        Window.clearcolor = (1, 1, 1, 1)

        # MIDI入力の設定
        params = self.read_params('params.txt')
        if params is not None:
            device1 = params.get('device1')
            device2 = params.get('device2')
            self.use_midi = int(params.get('use_midi', 0))
            self.map_data1 = params.get('map_data1')
            self.map_image1 = params.get('map_image1')
            self.map_data2 = params.get('map_data2')
            self.map_image2 = params.get('map_image2')
            self.map_data3 = params.get('map_data3')
            self.map_image3 = params.get('map_image3')
            # ... and so on for the other map_data and map_image parameters
        else:
            print("Error: Failed to read parameters")
            return None

        self.midi_inputs = []
        if self.use_midi > 0:
            midi_in1 = rtmidi.MidiIn()
            midi_in2 = rtmidi.MidiIn()
            midi_in1.open_port(int(device1))
            midi_in2.open_port(int(device2))
            self.midi_inputs = [midi_in1, midi_in2]


        # データベースの初期化
        self.conn = sqlite3.connect('events.db')
        cursor = self.conn.cursor()
        # gamesテーブルの作成
        cursor.execute('''
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
        ''')

        # eventsテーブルの作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            time TEXT,
            x_position INTEGER,
            y_position INTEGER,
            difference INTEGER, 
            velocity_player1 INTEGER,
            pitch_player1 INTEGER,
            velocity_player2 INTEGER,
            pitch_player2 INTEGER,
            is_overlapping BOOLEAN DEFAULT 0, 
            FOREIGN KEY (game_id) REFERENCES games (id)
        )
        ''')
        self.conn.commit()
        cursor.close()

        game = GameScreen(midi_inputs=self.midi_inputs, conn=self.conn, params=params)
        return game
    
    # ウィンドウが閉じられたときに呼び出される
    def on_stop(self):
        print("Window has been closed")

        if self.use_midi > 0:
            for midi_input in self.midi_inputs:
                midi_input.close_port()


    # パラメータファイルからMIDIデバイス番号を読み込む関数
    def read_params(self, file_name):
        params = {}
        with open(file_name, 'r', encoding='utf-8') as file:
            for line in file:
                key, value = line.strip().split('=')
                params[key] = value

        return params


if __name__ == '__main__':
    MidiballApp().run()