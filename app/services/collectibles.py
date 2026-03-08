"""Enoch Collectibles Engine — evaluates completed games for earned items.

Replays the game with python-chess to analyze positions, captures, promotions,
checks, and structures. Returns a list of earned item dicts."""

import chess

from app.services.collectibles_catalog import CATALOG


class GameAnalysis:
    """Pre-computes everything needed for trigger evaluation from a game's moves."""

    def __init__(self, game, moves, player_color):
        self.game = game
        self.player_color = player_color
        self.chess_color = chess.WHITE if player_color == 'white' else chess.BLACK
        self.opp_color = not self.chess_color
        self.result = game.result
        self.result_type = game.result_type or ''
        self.won = (self.result == '1-0' and self.chess_color == chess.WHITE) or \
                   (self.result == '0-1' and self.chess_color == chess.BLACK)
        self.lost = (self.result == '1-0' and self.chess_color == chess.BLACK) or \
                    (self.result == '0-1' and self.chess_color == chess.WHITE)
        self.drawn = self.result == '1/2-1/2'

        self.boards = []
        self.sans = [m.move_san for m in moves]
        self.ucis = [m.move_uci for m in moves]
        self.colors = [m.color for m in moves]
        self.total_half = len(moves)
        self.total_full = (self.total_half + 1) // 2

        board = chess.Board()
        self.boards.append(board.copy())
        self.captures_by_player = []
        self.captures_by_opp = []
        self.checks_by_player = []
        self.promotions_player = []
        self.castles_player = []
        self.en_passants_player = []
        self.king_moves_player = []
        self.pieces_moved_player = set()
        self.pawn_files_moved = {}
        self.material_history = []
        self.consecutive_no_capture = []

        no_capture_run = 0
        for i, m in enumerate(moves):
            mv = chess.Move.from_uci(m.move_uci)
            san = m.move_san
            is_mine = m.color == player_color

            captured = board.piece_at(mv.to_square)
            is_ep = board.is_en_passant(mv)
            if is_ep:
                captured_type = chess.PAWN
            elif captured:
                captured_type = captured.piece_type
            else:
                captured_type = None

            piece = board.piece_at(mv.from_square)
            piece_type = piece.piece_type if piece else None

            if is_mine:
                if piece_type:
                    self.pieces_moved_player.add((piece_type, mv.from_square))
                if piece_type == chess.KING and san not in ('O-O', 'O-O-O'):
                    self.king_moves_player.append(i)
                if piece_type == chess.PAWN:
                    f = chess.square_file(mv.from_square)
                    self.pawn_files_moved.setdefault(f, 0)
                    self.pawn_files_moved[f] += 1
                if san in ('O-O', 'O-O-O'):
                    self.castles_player.append((i, san))

            board.push(mv)
            self.boards.append(board.copy())

            if captured_type is not None or is_ep:
                no_capture_run = 0
                entry = {'idx': i, 'san': san, 'piece': captured_type, 'square': mv.to_square, 'is_ep': is_ep}
                if is_mine:
                    self.captures_by_player.append(entry)
                else:
                    self.captures_by_opp.append(entry)
            else:
                no_capture_run += 1

            self.consecutive_no_capture.append(no_capture_run)

            if is_mine and board.is_check():
                self.checks_by_player.append(i)

            if is_mine and mv.promotion:
                self.promotions_player.append({'idx': i, 'to': mv.promotion, 'square': mv.to_square})

            if is_mine and is_ep:
                self.en_passants_player.append(i)

            mat_w = sum(self._pv(p.piece_type) for p in board.piece_map().values() if p.color == chess.WHITE)
            mat_b = sum(self._pv(p.piece_type) for p in board.piece_map().values() if p.color == chess.BLACK)
            self.material_history.append((mat_w, mat_b))

        self.final_board = self.boards[-1] if self.boards else chess.Board()

    @staticmethod
    def _pv(pt):
        return {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}.get(pt, 0)

    def my_material(self, idx=-1):
        w, b = self.material_history[idx]
        return w if self.chess_color == chess.WHITE else b

    def opp_material(self, idx=-1):
        w, b = self.material_history[idx]
        return b if self.chess_color == chess.WHITE else w

    def material_diff(self, idx=-1):
        return self.my_material(idx) - self.opp_material(idx)

    def last_san(self):
        return self.sans[-1] if self.sans else ''

    def last_uci(self):
        return self.ucis[-1] if self.ucis else ''

    def player_castled(self):
        return len(self.castles_player) > 0

    def opp_piece_count(self, piece_type):
        return sum(1 for p in self.final_board.piece_map().values()
                   if p.color == self.opp_color and p.piece_type == piece_type)

    def my_pawn_count(self):
        return sum(1 for p in self.final_board.piece_map().values()
                   if p.color == self.chess_color and p.piece_type == chess.PAWN)


# ══════════════════════════════════════════════════════════════
# TRIGGER FUNCTIONS — each returns True/False
# ══════════════════════════════════════════════════════════════

def _capture_all_8_pawns(a):
    return a.won and sum(1 for c in a.captures_by_player if c['piece'] == chess.PAWN) >= 8

def _sacrifice_rook_and_win(a):
    lost_rooks = sum(1 for c in a.captures_by_opp if c['piece'] == chess.ROOK)
    return a.won and lost_rooks >= 1

def _win_no_pawn_captures(a):
    return a.won and all(c['piece'] != chess.PAWN for c in a.captures_by_player)

def _checkmate_zero_flight(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    fb = a.final_board
    king_sq = fb.king(a.opp_color)
    if king_sq is None:
        return False
    for sq in chess.SQUARES:
        if chess.square_distance(king_sq, sq) == 1:
            if fb.piece_at(sq) is None or fb.piece_at(sq).color == a.chess_color:
                continue
            return False
    return True

def _promote_to_knight(a):
    return any(p['to'] == chess.KNIGHT for p in a.promotions_player)

def _queens_traded_before_10(a):
    all_caps = sorted(a.captures_by_player + a.captures_by_opp, key=lambda c: c['idx'])
    queen_caps = [c for c in all_caps if c['piece'] == chess.QUEEN]
    return len(queen_caps) >= 2 and all(c['idx'] < 20 for c in queen_caps[:2])

def _opponent_early_blunder(a):
    if not a.won:
        return False
    for c in a.captures_by_player:
        if c['idx'] < 12 and c['piece'] in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            return True
    return False

def _five_slow_moves(a):
    return False

def _three_recaptures(a):
    count = 0
    all_caps = sorted(a.captures_by_player + a.captures_by_opp, key=lambda c: c['idx'])
    for i in range(1, len(all_caps)):
        if all_caps[i]['square'] == all_caps[i-1]['square'] and all_caps[i]['idx'] == all_caps[i-1]['idx'] + 1:
            is_mine = any(c is all_caps[i] for c in a.captures_by_player)
            if is_mine:
                count += 1
    return count >= 3

def _draw_threefold(a):
    return a.drawn and 'repetition' in a.result_type.lower() if a.result_type else False

def _checkmate_by_queenside_castle(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    return a.last_san() == 'O-O-O#'

def _push_same_pawn_4_times(a):
    return any(v >= 4 for v in a.pawn_files_moved.values())

def _checkmate_on_edge_file(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    uci = a.last_uci()
    dest_file = uci[2] if len(uci) >= 4 else ''
    return dest_file in ('a', 'h')

def _no_captures_15_moves(a):
    return any(r >= 30 for r in a.consecutive_no_capture)

def _capture_queen_with_pawn(a):
    for i, c in enumerate(a.captures_by_player):
        if c['piece'] == chess.QUEEN:
            san = c['san']
            if san and san[0].islower() and 'x' in san:
                return True
    return False

def _king_moves_5_before_20_win(a):
    early = sum(1 for idx in a.king_moves_player if idx < 40)
    return a.won and early >= 5

def _win_opp_has_both_rooks(a):
    return a.won and a.opp_piece_count(chess.ROOK) == 2

def _win_plus_10_material(a):
    return a.won and a.material_diff() >= 10

def _capture_on_own_back_ranks(a):
    if a.chess_color == chess.WHITE:
        back = [0, 1]
    else:
        back = [6, 7]
    for c in a.captures_by_player:
        rank = chess.square_rank(c['square'])
        if rank in back:
            return True
    return False

def _smothered_mate(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    fb = a.final_board
    king_sq = fb.king(a.opp_color)
    if king_sq is None:
        return False
    uci = a.last_uci()
    mating_sq = chess.parse_square(uci[2:4]) if len(uci) >= 4 else None
    mating_piece = fb.piece_at(mating_sq) if mating_sq is not None else None
    if not mating_piece or mating_piece.piece_type != chess.KNIGHT:
        return False
    for sq in chess.SquareSet(chess.BB_KING_ATTACKS[king_sq]):
        p = fb.piece_at(sq)
        if p is None or p.color == a.chess_color:
            return False
    return True

def _win_without_castling(a):
    return a.won and not a.player_castled()

def _king_escapes_3_checks_win(a):
    if not a.won:
        return False
    consec = 0
    for i in range(len(a.boards) - 1):
        if a.colors[i] != a.player_color and a.boards[i + 1].is_check() is False:
            pass
        b_before = a.boards[i]
        if i > 0 and a.colors[i-1] != a.player_color:
            if b_before.is_check():
                consec += 1
                if consec >= 3:
                    return True
            else:
                consec = 0
    opp_checks = []
    for i in range(len(a.sans)):
        if a.colors[i] != a.player_color and '+' in a.sans[i]:
            opp_checks.append(i)
    for j in range(len(opp_checks) - 2):
        if opp_checks[j+1] == opp_checks[j] + 2 and opp_checks[j+2] == opp_checks[j+1] + 2:
            return True
    return False

def _king_on_center_win(a):
    if not a.won:
        return False
    center = {chess.D4, chess.D5, chess.E4, chess.E5}
    king_sq = a.final_board.king(a.chess_color)
    return king_sq in center

def _create_doubled_pawns(a):
    for b in a.boards[1:]:
        files = {}
        for sq, p in b.piece_map().items():
            if p.color == a.opp_color and p.piece_type == chess.PAWN:
                f = chess.square_file(sq)
                files[f] = files.get(f, 0) + 1
        if any(v >= 2 for v in files.values()):
            return True
    return False

def _discovered_check_mate(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    if a.total_half < 2:
        return False
    uci = a.last_uci()
    mv = chess.Move.from_uci(uci)
    pre = a.boards[-2]
    piece = pre.piece_at(mv.from_square)
    if piece and piece.piece_type != chess.KNIGHT:
        post = a.final_board
        checkers = post.checkers()
        if checkers and mv.to_square not in checkers:
            return True
    return False

def _opponent_resigns_after_check(a):
    if a.result_type != 'resignation' or not a.won:
        return False
    if a.total_half >= 2:
        idx = a.total_half - 1
        if a.colors[idx] != a.player_color and idx > 0:
            prev_san = a.sans[idx - 1]
            return '+' in prev_san
        if a.colors[idx] == a.player_color:
            return '+' in a.sans[idx]
    return False

def _opponent_timeout_winning(a):
    return False

def _king_captures_piece(a):
    for s in a.sans:
        if s.startswith('Kx'):
            return True
    return False

def _win_with_tripled_pawns(a):
    if not a.won:
        return False
    for b in a.boards:
        files = {}
        for sq, p in b.piece_map().items():
            if p.color == a.chess_color and p.piece_type == chess.PAWN:
                f = chess.square_file(sq)
                files[f] = files.get(f, 0) + 1
        if any(v >= 3 for v in files.values()):
            return True
    return False

def _draw_50_move_rule(a):
    return a.drawn and a.result_type == 'draw'

def _promote_then_lose(a):
    for p in a.promotions_player:
        promo_idx = p['idx']
        promo_sq = p['square']
        for c in a.captures_by_opp:
            if c['idx'] == promo_idx + 1 and c['square'] == promo_sq:
                return True
    return False

def _en_passant(a):
    return len(a.en_passants_player) > 0

def _checkmate_with_bishop(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    uci = a.last_uci()
    sq = chess.parse_square(uci[2:4]) if len(uci) >= 4 else None
    p = a.final_board.piece_at(sq) if sq is not None else None
    return p is not None and p.piece_type == chess.BISHOP

def _win_down_queen(a):
    if not a.won:
        return False
    lost_queen = any(c['piece'] == chess.QUEEN for c in a.captures_by_opp)
    has_queen = any(p.piece_type == chess.QUEEN and p.color == a.chess_color
                    for p in a.final_board.piece_map().values())
    return lost_queen and not has_queen

def _no_pawn_captures_10(a):
    for start in range(len(a.boards) - 20):
        window = a.boards[start:start+21]
        found = False
        for b in window:
            if b.has_legal_en_passant():
                found = True
                break
        if not found:
            has_pawn_cap = False
            for j in range(start, min(start + 20, a.total_half)):
                if 'x' in a.sans[j]:
                    b_pre = a.boards[j]
                    mv = chess.Move.from_uci(a.ucis[j])
                    p = b_pre.piece_at(mv.from_square)
                    if p and p.piece_type == chess.PAWN:
                        has_pawn_cap = True
                        break
            if not has_pawn_cap:
                return True
    return False

def _break_pin_with_capture(a):
    for i in range(len(a.sans)):
        if a.colors[i] == a.player_color and 'x' in a.sans[i]:
            b_pre = a.boards[i]
            if b_pre.is_check():
                continue
            king_sq = b_pre.king(a.chess_color)
            if king_sq is None:
                continue
            mv = chess.Move.from_uci(a.ucis[i])
            capture_sq = mv.to_square
            for sq in b_pre.piece_map():
                piece = b_pre.piece_at(sq)
                if piece and piece.color == a.chess_color and b_pre.is_pinned(a.chess_color, sq):
                    pin_ray = b_pre.pin(a.chess_color, sq)
                    if capture_sq in chess.SquareSet(pin_ray):
                        return True
    return False

def _opponent_timeout_close(a):
    return False

def _queen_sacrifice_win(a):
    if not a.won:
        return False
    return any(c['piece'] == chess.QUEEN for c in a.captures_by_opp) and \
        not any(p.piece_type == chess.QUEEN and p.color == a.chess_color
                for p in a.final_board.piece_map().values())

def _blunder_but_win(a):
    return False

def _promote_to_bishop(a):
    return any(p['to'] == chess.BISHOP for p in a.promotions_player)

def _win_after_losing_3_minors(a):
    if not a.won:
        return False
    lost_minors = sum(1 for c in a.captures_by_opp
                      if c['piece'] in (chess.KNIGHT, chess.BISHOP))
    return lost_minors >= 3

def _back_rank_mate(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    king_sq = a.final_board.king(a.opp_color)
    if king_sq is None:
        return False
    back_rank = 0 if a.opp_color == chess.WHITE else 7
    return chess.square_rank(king_sq) == back_rank

def _king_forced_to_start(a):
    start_sq = chess.E8 if a.opp_color == chess.BLACK else chess.E1
    opp_king_moved = False
    for i in range(len(a.sans)):
        if a.colors[i] != a.player_color:
            b = a.boards[i]
            king_sq = b.king(a.opp_color)
            if king_sq != start_sq:
                opp_king_moved = True
    final_king = a.final_board.king(a.opp_color)
    return opp_king_moved and final_king == start_sq

def _win_last_second(a):
    return False

def _sacrifice_knight_win(a):
    if not a.won:
        return False
    return any(c['piece'] == chess.KNIGHT for c in a.captures_by_opp)

def _mutual_consecutive_captures(a):
    all_caps = sorted(a.captures_by_player + a.captures_by_opp, key=lambda c: c['idx'])
    for i in range(1, len(all_caps)):
        if all_caps[i]['idx'] == all_caps[i-1]['idx'] + 1:
            return True
    return False

def _move_all_pieces_before_25(a):
    moved = set()
    b = chess.Board()
    for sq, p in b.piece_map().items():
        if p.color == a.chess_color:
            moved_key = (p.piece_type, sq)
    initial = set()
    b = chess.Board()
    for sq, p in b.piece_map().items():
        if p.color == a.chess_color:
            initial.add(sq)
    moved_sqs = set()
    for i in range(min(50, a.total_half)):
        if a.colors[i] == a.player_color:
            mv = chess.Move.from_uci(a.ucis[i])
            if mv.from_square in initial:
                moved_sqs.add(mv.from_square)
    return len(moved_sqs) >= 16

def _discovered_attack_capture(a):
    for i in range(len(a.captures_by_player)):
        c = a.captures_by_player[i]
        idx = c['idx']
        if idx < 1:
            continue
        b_pre = a.boards[idx]
        mv = chess.Move.from_uci(a.ucis[idx])
        piece = b_pre.piece_at(mv.from_square)
        if piece and piece.piece_type != chess.PAWN:
            b_post = a.boards[idx + 1]
            if b_post.is_check() and mv.to_square not in b_post.checkers():
                return True
    return False

def _double_check_mate(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    checkers = a.final_board.checkers()
    return len(checkers) >= 2

def _capture_on_just_moved_square(a):
    for c in a.captures_by_player:
        idx = c['idx']
        if idx >= 1:
            prev_uci = a.ucis[idx - 1]
            prev_dest = prev_uci[2:4] if len(prev_uci) >= 4 else ''
            my_dest = a.ucis[idx][2:4] if len(a.ucis[idx]) >= 4 else ''
            if prev_dest == my_dest:
                return True
    return False

def _win_no_time_pressure(a):
    return False

def _center_pawns_by_move_3(a):
    if a.chess_color == chess.WHITE:
        targets = {'d2d4', 'e2e4'}
    else:
        targets = {'d7d5', 'e7e5'}
    found = set()
    for i in range(min(6, a.total_half)):
        if a.colors[i] == a.player_color:
            if a.ucis[i] in targets:
                found.add(a.ucis[i])
    return len(found) >= 2

def _ten_fast_moves_win(a):
    return False

def _four_consecutive_captures(a):
    consec = 0
    for i in range(a.total_half):
        if a.colors[i] == a.player_color and 'x' in a.sans[i]:
            consec += 1
            if consec >= 4:
                return True
        elif a.colors[i] == a.player_color:
            consec = 0
    return False

def _promote_to_rook(a):
    return any(p['to'] == chess.ROOK for p in a.promotions_player)

def _five_recapture_trades(a):
    count = 0
    all_caps = sorted(a.captures_by_player + a.captures_by_opp, key=lambda c: c['idx'])
    for i in range(1, len(all_caps)):
        if all_caps[i]['square'] == all_caps[i-1]['square'] and all_caps[i]['idx'] == all_caps[i-1]['idx'] + 1:
            count += 1
    return count >= 5

def _resign_after_queen_capture(a):
    if not (a.won and a.result_type == 'resignation'):
        return False
    if a.captures_by_player:
        last_cap = max(a.captures_by_player, key=lambda c: c['idx'])
        if last_cap['piece'] == chess.QUEEN and last_cap['idx'] >= a.total_half - 2:
            return True
    return False

def _survive_blundered_mate(a):
    return False

def _game_exceeds_70(a):
    return a.total_full > 70

def _opponent_loses_on_time(a):
    return a.won and a.result_type == 'forfeit'

def _checkmate_on_move_60(a):
    return a.won and a.result_type == 'checkmate' and a.total_full == 60

def _knight_fork_major(a):
    for i in range(len(a.sans)):
        if a.colors[i] != a.player_color:
            continue
        san = a.sans[i]
        if not san.startswith('N'):
            continue
        b_post = a.boards[i + 1]
        mv = chess.Move.from_uci(a.ucis[i])
        attacked = set()
        for atk_sq in b_post.attacks(mv.to_square):
            p = b_post.piece_at(atk_sq)
            if p and p.color == a.opp_color and p.piece_type in (chess.QUEEN, chess.ROOK, chess.KING):
                attacked.add(p.piece_type)
        if len(attacked) >= 2:
            for c in a.captures_by_player:
                if c['idx'] == i + 2 or c['idx'] == i + 1:
                    if c['piece'] in (chess.QUEEN, chess.ROOK):
                        return True
    return False

def _five_plus_blunders(a):
    return False

def _symmetric_to_move_6(a):
    for i in range(0, min(12, a.total_half), 2):
        if i + 1 >= a.total_half:
            return False
        w_uci = a.ucis[i]
        b_uci = a.ucis[i + 1]
        w_from, w_to = w_uci[:2], w_uci[2:4]
        b_from, b_to = b_uci[:2], b_uci[2:4]

        def mirror(sq):
            return sq[0] + str(9 - int(sq[1]))

        if b_from != mirror(w_from) or b_to != mirror(w_to):
            return False
    return a.total_half >= 12

def _draw_before_20(a):
    return a.drawn and a.total_full < 20

def _checkmate_with_pawn(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    uci = a.last_uci()
    sq = chess.parse_square(uci[2:4]) if len(uci) >= 4 else None
    if sq is None:
        return False
    p = a.final_board.piece_at(sq)
    return p is not None and p.piece_type == chess.PAWN

def _edge_pawn_move_1(a):
    edge_ucis_w = {'a2a4', 'h2h4', 'a2a3', 'h2h3'}
    edge_ucis_b = {'a7a5', 'h7h5', 'a7a6', 'h7h6'}
    target = edge_ucis_w if a.chess_color == chess.WHITE else edge_ucis_b
    for i in range(min(4, a.total_half)):
        if a.colors[i] == a.player_color and a.ucis[i] in target:
            return True
    return False

def _en_passant_escapes_check(a):
    for ep_idx in a.en_passants_player:
        b_pre = a.boards[ep_idx]
        if b_pre.is_check():
            return True
    return False

def _five_or_more_checks(a):
    return len(a.checks_by_player) >= 5

def _mate_in_3(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    if a.total_half < 6:
        return False
    last_6 = a.sans[-6:]
    checks = sum(1 for s in last_6 if '+' in s or '#' in s)
    return checks >= 3

def _draw_insufficient_material(a):
    return a.drawn and a.result_type == 'draw'

def _slow_then_book_move(a):
    return False

def _no_pawn_moves_15(a):
    for start in range(a.total_half - 29):
        pawn_moved = False
        for j in range(start, start + 30):
            if j >= a.total_half:
                break
            b = a.boards[j]
            mv = chess.Move.from_uci(a.ucis[j])
            p = b.piece_at(mv.from_square)
            if p and p.piece_type == chess.PAWN:
                pawn_moved = True
                break
        if not pawn_moved:
            return True
    return False

def _opponent_abandons(a):
    return a.won and a.result_type in ('forfeit', 'abandon')

def _two_promotions(a):
    return len(a.promotions_player) >= 2

def _king_pawn_endgame_win(a):
    if not a.won:
        return False
    for sq, p in a.final_board.piece_map().items():
        if p.piece_type not in (chess.KING, chess.PAWN):
            return False
    return True

def _big_lead_then_lose(a):
    if not a.lost:
        return False
    return any(a.material_diff(i) >= 5 for i in range(len(a.material_history)))

def _win_7_8_pawns(a):
    return a.won and a.my_pawn_count() >= 7

def _dormant_piece_checks(a):
    if a.total_half < 60:
        return False
    piece_last_moved = {}
    for i in range(a.total_half):
        if a.colors[i] == a.player_color:
            mv = chess.Move.from_uci(a.ucis[i])
            piece_last_moved[mv.to_square] = i
            if mv.from_square in piece_last_moved:
                piece_last_moved[mv.to_square] = i
    for i in range(a.total_half):
        if a.colors[i] == a.player_color and '+' in a.sans[i]:
            mv = chess.Move.from_uci(a.ucis[i])
            last = piece_last_moved.get(mv.from_square, i)
            if i - last >= 60:
                return True
    return False

def _opponent_aborts(a):
    return a.total_half <= 2 and a.won

def _win_no_pieces_lost(a):
    return a.won and len(a.captures_by_opp) == 0

def _control_center_pawns(a):
    center = {chess.D4, chess.E4, chess.D5, chess.E5}
    for b in a.boards:
        controlled = set()
        for sq in center:
            p = b.piece_at(sq)
            if p and p.color == a.chess_color and p.piece_type == chess.PAWN:
                controlled.add(sq)
        if len(controlled) >= 4:
            return True
    return False

def _game_exceeds_100(a):
    return a.total_full > 100

def _win_always_low_time(a):
    return False

def _draw_timeout_insufficient(a):
    return a.drawn and 'insufficient' in (a.result_type or '').lower()

def _win_between_2am_4am(a):
    if not a.won or not a.game.completed_at:
        return False
    h = a.game.completed_at.hour
    return 2 <= h < 4

def _checkmate_on_move_50(a):
    return a.won and a.result_type == 'checkmate' and a.total_full == 50

def _trap_queen(a):
    for c in a.captures_by_player:
        if c['piece'] == chess.QUEEN:
            return True
    return False

def _diagonal_pawn_chain_4(a):
    for b in a.boards:
        pawns = set()
        for sq, p in b.piece_map().items():
            if p.color == a.chess_color and p.piece_type == chess.PAWN:
                pawns.add(sq)
        for sq in pawns:
            chain = 1
            cur = sq
            while True:
                f, r = chess.square_file(cur), chess.square_rank(cur)
                nxt_f = f + 1
                nxt_r = r + (1 if a.chess_color == chess.WHITE else -1)
                if 0 <= nxt_f <= 7 and 0 <= nxt_r <= 7:
                    nxt = chess.square(nxt_f, nxt_r)
                    if nxt in pawns:
                        chain += 1
                        cur = nxt
                        continue
                break
            if chain >= 4:
                return True
    return False

def _patient_win(a):
    return False

def _premove_checkmate(a):
    return False

def _no_captures_10_moves(a):
    return any(r >= 20 for r in a.consecutive_no_capture)

def _checkmate_by_kingside_castle(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    return a.last_san() == 'O-O#'

def _knight_outpost_5_turns(a):
    knight_positions = {}
    for i in range(a.total_half):
        if a.colors[i] == a.player_color:
            mv = chess.Move.from_uci(a.ucis[i])
            b = a.boards[i]
            p = b.piece_at(mv.from_square)
            if p and p.piece_type == chess.KNIGHT:
                for sq in list(knight_positions.keys()):
                    if sq == mv.from_square:
                        del knight_positions[sq]
                knight_positions[mv.to_square] = i
            else:
                for sq in list(knight_positions.keys()):
                    if sq == mv.from_square:
                        del knight_positions[sq]
        else:
            for sq, start_idx in list(knight_positions.items()):
                turns_held = (i - start_idx) // 2
                if turns_held >= 5:
                    return True
    return False

def _four_pawns_first_4(a):
    pawn_files = set()
    count = 0
    for i in range(min(8, a.total_half)):
        if a.colors[i] == a.player_color:
            count += 1
            b = a.boards[i]
            mv = chess.Move.from_uci(a.ucis[i])
            p = b.piece_at(mv.from_square)
            if p and p.piece_type == chess.PAWN:
                pawn_files.add(chess.square_file(mv.from_square))
            if count >= 4:
                break
    return len(pawn_files) >= 4

def _block_check_with_pawn(a):
    for i in range(a.total_half):
        if a.colors[i] == a.player_color:
            b_pre = a.boards[i]
            if b_pre.is_check():
                mv = chess.Move.from_uci(a.ucis[i])
                p = b_pre.piece_at(mv.from_square)
                if p and p.piece_type == chess.PAWN and 'x' not in a.sans[i]:
                    return True
    return False

def _sever_rook_connection(a):
    for i in range(a.total_half):
        if a.colors[i] != a.player_color:
            continue
        b_pre = a.boards[i]
        b_post = a.boards[i + 1]
        opp_rooks_pre = [sq for sq, p in b_pre.piece_map().items()
                         if p.color == a.opp_color and p.piece_type == chess.ROOK]
        if len(opp_rooks_pre) != 2:
            continue
        r1, r2 = opp_rooks_pre
        if chess.square_rank(r1) == chess.square_rank(r2):
            mv = chess.Move.from_uci(a.ucis[i])
            dest_rank = chess.square_rank(mv.to_square)
            if dest_rank == chess.square_rank(r1):
                f1, f2 = sorted([chess.square_file(r1), chess.square_file(r2)])
                fd = chess.square_file(mv.to_square)
                if f1 < fd < f2:
                    return True
    return False

def _comeback_from_minus_5(a):
    if not a.won:
        return False
    return any(a.material_diff(i) <= -5 for i in range(len(a.material_history)))

def _king_moves_once(a):
    if not a.won:
        return False
    non_castle_king = [idx for idx in a.king_moves_player]
    return len(non_castle_king) == 1

def _brilliant_forced_mate(a):
    return False


# ══════════════════════════════════════════════════════════════
# BATCH 2 — GAME-ANALYSIS TRIGGERS (items 131–148)
# ══════════════════════════════════════════════════════════════

def _win_only_2_piece_types(a):
    if not a.won or not a.captures_by_player:
        return False
    capturing_types = set()
    for c in a.captures_by_player:
        b = a.boards[c['idx']]
        mv = chess.Move.from_uci(a.ucis[c['idx']])
        p = b.piece_at(mv.from_square)
        if p:
            capturing_types.add(p.piece_type)
    return len(capturing_types) <= 2


def _checkmate_with_knight(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    uci = a.last_uci()
    sq = chess.parse_square(uci[2:4]) if len(uci) >= 4 else None
    if sq is None:
        return False
    p = a.final_board.piece_at(sq)
    return p is not None and p.piece_type == chess.KNIGHT


def _only_pawn_moves_first_5(a):
    if not a.won:
        return False
    count = 0
    for i in range(a.total_half):
        if a.colors[i] == a.player_color:
            count += 1
            if count > 5:
                break
            b = a.boards[i]
            mv = chess.Move.from_uci(a.ucis[i])
            p = b.piece_at(mv.from_square)
            if not p or p.piece_type != chess.PAWN:
                return False
    return count >= 5


def _checkmate_under_15_moves(a):
    return a.won and a.result_type == 'checkmate' and a.total_full <= 15


def _win_queen_never_moved(a):
    if not a.won:
        return False
    queen_start = chess.D1 if a.chess_color == chess.WHITE else chess.D8
    for i in range(a.total_half):
        if a.colors[i] == a.player_color:
            mv = chess.Move.from_uci(a.ucis[i])
            if mv.from_square == queen_start:
                return False
            for prev_c in a.captures_by_opp:
                if prev_c['square'] == queen_start and prev_c['idx'] < i:
                    return a.won
    return True


def _three_captures_same_file(a):
    from collections import Counter
    files = Counter()
    for c in a.captures_by_player:
        f = chess.square_file(c['square'])
        files[f] += 1
    return any(v >= 3 for v in files.values())


def _comeback_from_minus_3(a):
    if not a.won:
        return False
    return any(a.material_diff(i) <= -3 for i in range(len(a.material_history)))


def _never_doubled_pawns(a):
    if not a.won:
        return False
    for b in a.boards:
        files = {}
        for sq, p in b.piece_map().items():
            if p.color == a.chess_color and p.piece_type == chess.PAWN:
                f = chess.square_file(sq)
                files[f] = files.get(f, 0) + 1
        if any(v >= 2 for v in files.values()):
            return False
    return True


def _game_25_to_30_moves(a):
    return a.won and 25 <= a.total_full <= 30


def _three_pawns_on_7th(a):
    rank7 = 6 if a.chess_color == chess.WHITE else 1
    for b in a.boards:
        count = 0
        for sq, p in b.piece_map().items():
            if p.color == a.chess_color and p.piece_type == chess.PAWN:
                if chess.square_rank(sq) == rank7:
                    count += 1
        if count >= 3:
            return True
    return False


def _long_range_mate(a):
    if not (a.won and a.result_type == 'checkmate'):
        return False
    uci = a.last_uci()
    if len(uci) < 4:
        return False
    f1, r1 = ord(uci[0]) - ord('a'), int(uci[1]) - 1
    f2, r2 = ord(uci[2]) - ord('a'), int(uci[3]) - 1
    dist = max(abs(f2 - f1), abs(r2 - r1))
    return dist >= 4


def _win_no_captures_first_15(a):
    if not a.won:
        return False
    all_caps = a.captures_by_player + a.captures_by_opp
    for c in all_caps:
        if c['idx'] < 30:
            return False
    return True


def _piece_unmoved_20_turns(a):
    initial_pieces = {}
    b0 = chess.Board()
    for sq, p in b0.piece_map().items():
        if p.color == a.chess_color and p.piece_type not in (chess.PAWN, chess.KING):
            initial_pieces[sq] = 0

    piece_positions = dict(initial_pieces)

    for i in range(a.total_half):
        if a.colors[i] == a.player_color:
            mv = chess.Move.from_uci(a.ucis[i])
            if mv.from_square in piece_positions:
                del piece_positions[mv.from_square]
            b = a.boards[i]
            p = b.piece_at(mv.from_square)
            if p and p.piece_type not in (chess.PAWN, chess.KING):
                piece_positions[mv.to_square] = i
        for sq, start_idx in list(piece_positions.items()):
            half_since = i - start_idx
            if half_since >= 40:
                return True
    return False


def _control_20_squares(a):
    for b in a.boards:
        attacked = set()
        for sq, p in b.piece_map().items():
            if p.color == a.chess_color:
                attacked.update(b.attacks(sq))
        if len(attacked) >= 20:
            return True
    return False


def _three_black_wins_streak(a):
    return False


def _capture_all_minors(a):
    knights = sum(1 for c in a.captures_by_player if c['piece'] == chess.KNIGHT)
    bishops = sum(1 for c in a.captures_by_player if c['piece'] == chess.BISHOP)
    return knights >= 2 and bishops >= 2


def _win_after_pawn_promote_queen(a):
    if not a.won:
        return False
    return any(p['to'] == chess.QUEEN for p in a.promotions_player)


def _ten_checkmates_career(a):
    return False


TRIGGERS = {
    'capture_all_8_pawns': _capture_all_8_pawns,
    'sacrifice_rook_and_win': _sacrifice_rook_and_win,
    'win_no_pawn_captures': _win_no_pawn_captures,
    'checkmate_zero_flight': _checkmate_zero_flight,
    'promote_to_knight': _promote_to_knight,
    'queens_traded_before_10': _queens_traded_before_10,
    'opponent_early_blunder': _opponent_early_blunder,
    'five_slow_moves': _five_slow_moves,
    'three_recaptures': _three_recaptures,
    'draw_threefold': _draw_threefold,
    'checkmate_by_queenside_castle': _checkmate_by_queenside_castle,
    'push_same_pawn_4_times': _push_same_pawn_4_times,
    'checkmate_on_edge_file': _checkmate_on_edge_file,
    'no_captures_15_moves': _no_captures_15_moves,
    'capture_queen_with_pawn': _capture_queen_with_pawn,
    'king_moves_5_before_20_win': _king_moves_5_before_20_win,
    'win_opp_has_both_rooks': _win_opp_has_both_rooks,
    'win_plus_10_material': _win_plus_10_material,
    'capture_on_own_back_ranks': _capture_on_own_back_ranks,
    'smothered_mate': _smothered_mate,
    'win_without_castling': _win_without_castling,
    'king_escapes_3_checks_win': _king_escapes_3_checks_win,
    'king_on_center_win': _king_on_center_win,
    'create_doubled_pawns': _create_doubled_pawns,
    'discovered_check_mate': _discovered_check_mate,
    'opponent_resigns_after_check': _opponent_resigns_after_check,
    'opponent_timeout_winning': _opponent_timeout_winning,
    'king_captures_piece': _king_captures_piece,
    'win_with_tripled_pawns': _win_with_tripled_pawns,
    'draw_50_move_rule': _draw_50_move_rule,
    'promote_then_lose': _promote_then_lose,
    'en_passant': _en_passant,
    'checkmate_with_bishop': _checkmate_with_bishop,
    'win_down_queen': _win_down_queen,
    'no_pawn_captures_10': _no_pawn_captures_10,
    'break_pin_with_capture': _break_pin_with_capture,
    'opponent_timeout_close': _opponent_timeout_close,
    'queen_sacrifice_win': _queen_sacrifice_win,
    'blunder_but_win': _blunder_but_win,
    'promote_to_bishop': _promote_to_bishop,
    'win_after_losing_3_minors': _win_after_losing_3_minors,
    'back_rank_mate': _back_rank_mate,
    'king_forced_to_start': _king_forced_to_start,
    'win_last_second': _win_last_second,
    'sacrifice_knight_win': _sacrifice_knight_win,
    'mutual_consecutive_captures': _mutual_consecutive_captures,
    'move_all_pieces_before_25': _move_all_pieces_before_25,
    'discovered_attack_capture': _discovered_attack_capture,
    'double_check_mate': _double_check_mate,
    'capture_on_just_moved_square': _capture_on_just_moved_square,
    'win_no_time_pressure': _win_no_time_pressure,
    'center_pawns_by_move_3': _center_pawns_by_move_3,
    'ten_fast_moves_win': _ten_fast_moves_win,
    'four_consecutive_captures': _four_consecutive_captures,
    'promote_to_rook': _promote_to_rook,
    'five_recapture_trades': _five_recapture_trades,
    'resign_after_queen_capture': _resign_after_queen_capture,
    'survive_blundered_mate': _survive_blundered_mate,
    'game_exceeds_70': _game_exceeds_70,
    'opponent_loses_on_time': _opponent_loses_on_time,
    'checkmate_on_move_60': _checkmate_on_move_60,
    'knight_fork_major': _knight_fork_major,
    'five_plus_blunders': _five_plus_blunders,
    'symmetric_to_move_6': _symmetric_to_move_6,
    'draw_before_20': _draw_before_20,
    'checkmate_with_pawn': _checkmate_with_pawn,
    'edge_pawn_move_1': _edge_pawn_move_1,
    'en_passant_escapes_check': _en_passant_escapes_check,
    'five_or_more_checks': _five_or_more_checks,
    'mate_in_3': _mate_in_3,
    'draw_insufficient_material': _draw_insufficient_material,
    'slow_then_book_move': _slow_then_book_move,
    'no_pawn_moves_15': _no_pawn_moves_15,
    'opponent_abandons': _opponent_abandons,
    'two_promotions': _two_promotions,
    'king_pawn_endgame_win': _king_pawn_endgame_win,
    'big_lead_then_lose': _big_lead_then_lose,
    'win_7_8_pawns': _win_7_8_pawns,
    'dormant_piece_checks': _dormant_piece_checks,
    'opponent_aborts': _opponent_aborts,
    'win_no_pieces_lost': _win_no_pieces_lost,
    'control_center_pawns': _control_center_pawns,
    'game_exceeds_100': _game_exceeds_100,
    'win_always_low_time': _win_always_low_time,
    'draw_timeout_insufficient': _draw_timeout_insufficient,
    'win_between_2am_4am': _win_between_2am_4am,
    'checkmate_on_move_50': _checkmate_on_move_50,
    'trap_queen': _trap_queen,
    'diagonal_pawn_chain_4': _diagonal_pawn_chain_4,
    'patient_win': _patient_win,
    'premove_checkmate': _premove_checkmate,
    'no_captures_10_moves': _no_captures_10_moves,
    'checkmate_by_kingside_castle': _checkmate_by_kingside_castle,
    'knight_outpost_5_turns': _knight_outpost_5_turns,
    'four_pawns_first_4': _four_pawns_first_4,
    'block_check_with_pawn': _block_check_with_pawn,
    'sever_rook_connection': _sever_rook_connection,
    'comeback_from_minus_5': _comeback_from_minus_5,
    'king_moves_once': _king_moves_once,
    'brilliant_forced_mate': _brilliant_forced_mate,
    # batch 2 game-analysis triggers
    'win_only_2_piece_types': _win_only_2_piece_types,
    'checkmate_with_knight': _checkmate_with_knight,
    'only_pawn_moves_first_5': _only_pawn_moves_first_5,
    'checkmate_under_15_moves': _checkmate_under_15_moves,
    'win_queen_never_moved': _win_queen_never_moved,
    'three_captures_same_file': _three_captures_same_file,
    'comeback_from_minus_3': _comeback_from_minus_3,
    'never_doubled_pawns': _never_doubled_pawns,
    'game_25_to_30_moves': _game_25_to_30_moves,
    'three_pawns_on_7th': _three_pawns_on_7th,
    'long_range_mate': _long_range_mate,
    'win_no_captures_first_15': _win_no_captures_first_15,
    'piece_unmoved_20_turns': _piece_unmoved_20_turns,
    'control_20_squares': _control_20_squares,
    'three_black_wins_streak': _three_black_wins_streak,
    'capture_all_minors': _capture_all_minors,
    'win_after_pawn_promote_queen': _win_after_pawn_promote_queen,
    'ten_checkmates_career': _ten_checkmates_career,
}


def evaluate_collectibles(game, moves, player_color):
    """Run all trigger checks for a player. Returns list of earned catalog items."""
    try:
        analysis = GameAnalysis(game, moves, player_color)
    except Exception:
        return []

    earned = []
    for item in CATALOG:
        trigger_fn = TRIGGERS.get(item['trigger'])
        if not trigger_fn:
            continue
        try:
            if trigger_fn(analysis):
                earned.append(item)
        except Exception:
            continue

    return earned
