import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime

# データベースの接続
conn = sqlite3.connect('events.db')
cursor = conn.cursor()

# イベントデータの取得
cursor.execute("SELECT time, x_position, y_position FROM events")
data = cursor.fetchall()

# データを時間、X位置、Y位置に分解
times, x_positions, y_positions = [], [], []
for row in data:
    time_str, x, y = row
    time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    times.append(time)
    x_positions.append(x)
    y_positions.append(y-100)

# X位置とY位置の差の計算
xy_differences = [x - y for x, y in zip(x_positions, y_positions)]

# グラフの作成
plt.figure(figsize=(10, 5))
plt.plot(times, x_positions, label='X Position')
plt.plot(times, y_positions, label='Y Position')
plt.plot(times, xy_differences, label='Difference between X and Y Positions')
plt.xlabel('Time')
plt.ylabel('Value')
plt.title('X Position, Y Position, and Their Difference Over Time')
plt.legend()
plt.show()

conn.close()