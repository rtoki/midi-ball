import sqlite3
import csv

def fetch_db_data(cursor):
    # gamesテーブルからデータを取得
    cursor.execute("SELECT * FROM games")
    games_data = cursor.fetchall()

    # eventsテーブルからデータを取得
    cursor.execute("SELECT * FROM events")
    events_data = cursor.fetchall()

    return games_data, events_data

def write_to_csv(games_data, events_data):
    # gamesデータをCSVに書き込む
    with open('games1216.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "current_map_index", "end_time", "score", "score_player1", "score_player2", "restart_count", "elapsed_time"])  # ヘッダー行
        writer.writerows(games_data)  # データ行

    # eventsデータをCSVに書き込む
    with open('events1216.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "game_id", "time", "x_position", "y_position", "difference", "is_overlapping", "velocity_player1", "pitch_player1", "velocity_player2", "pitch_player2"])  # ヘッダー行
        writer.writerows(events_data)  # データ行

def main():
    # データベースへの接続
    conn = sqlite3.connect('events1216.db')
    cursor = conn.cursor()

    # データベースからデータを取得
    games_data, events_data = fetch_db_data(cursor)

    # CSVファイルにデータを書き込む
    write_to_csv(games_data, events_data)

    # データベースの接続を閉じる
    conn.close()

if __name__ == "__main__":
    main()
