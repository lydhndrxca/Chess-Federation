import chess


class ChessEngine:
    PIECE_VALUES = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,
    }

    @staticmethod
    def new_game():
        return chess.STARTING_FEN

    @staticmethod
    def get_legal_moves(fen):
        board = chess.Board(fen)
        moves = []
        for move in board.legal_moves:
            moves.append({
                'uci': move.uci(),
                'san': board.san(move),
                'from': chess.square_name(move.from_square),
                'to': chess.square_name(move.to_square),
                'promotion': move.promotion is not None,
            })
        return moves

    @staticmethod
    def make_move(fen, uci_move):
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci_move)
        if move not in board.legal_moves:
            raise ValueError(f'Illegal move: {uci_move}')
        san = board.san(move)
        board.push(move)
        if board.turn == chess.WHITE:
            move_number = board.fullmove_number - 1
        else:
            move_number = board.fullmove_number
        return {
            'fen': board.fen(),
            'san': san,
            'move_number': move_number,
            'turn': 'white' if board.turn == chess.WHITE else 'black',
        }

    @staticmethod
    def is_game_over(fen):
        board = chess.Board(fen)
        if not board.is_game_over():
            return False, None
        if board.is_checkmate():
            return True, 'checkmate'
        if board.is_stalemate():
            return True, 'stalemate'
        return True, 'draw'

    @staticmethod
    def get_material(fen):
        board = chess.Board(fen)
        white = sum(
            ChessEngine.PIECE_VALUES.get(p.piece_type, 0)
            for p in board.piece_map().values() if p.color == chess.WHITE
        )
        black = sum(
            ChessEngine.PIECE_VALUES.get(p.piece_type, 0)
            for p in board.piece_map().values() if p.color == chess.BLACK
        )
        return {'white': white, 'black': black}

    @staticmethod
    def get_turn(fen):
        board = chess.Board(fen)
        return 'white' if board.turn == chess.WHITE else 'black'

    @staticmethod
    def get_board_state(fen):
        board = chess.Board(fen)
        pieces = {}
        for square, piece in board.piece_map().items():
            pieces[chess.square_name(square)] = {
                'type': piece.symbol(),
                'color': 'white' if piece.color == chess.WHITE else 'black',
            }
        return {
            'pieces': pieces,
            'turn': 'white' if board.turn == chess.WHITE else 'black',
            'in_check': board.is_check(),
            'fen': fen,
        }

    @staticmethod
    def build_pgn(moves, game):
        headers = [
            f'[White "{game.white.username}"]',
            f'[Black "{game.black.username}"]',
            f'[Result "{game.result or "*"}"]',
            '',
        ]
        pgn_parts = []
        for move in moves:
            if move.color == 'white':
                pgn_parts.append(f'{move.move_number}.')
            pgn_parts.append(move.move_san)
        if game.result:
            pgn_parts.append(game.result)
        return '\n'.join(headers) + ' '.join(pgn_parts)
