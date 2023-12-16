class MapLoader:
    @staticmethod
    def load_map(file_path):
        map_data = []
        with open(file_path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                row = [int(cell) for cell in line.strip().split(',')]
                map_data.append(row)
        return map_data