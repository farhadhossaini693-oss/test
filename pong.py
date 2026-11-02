"""
1970s Retro Pong Arcade Game (Atari 1972 Homage)
Built with Pygame-CE & NumPy.
"""

from __future__ import annotations

import math
import random
import sys
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple

import pygame

# Initialize pygame core
pygame.init()

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PADDLE_WIDTH = 14
PADDLE_HEIGHT = 86
BALL_SIZE = 14
WINNING_SCORE = 11

PADDLE_SPEED = 520.0  # pixels per second
INITIAL_BALL_SPEED = 430.0  # pixels per second
SPEED_INCREMENT = 1.05  # speed boost per paddle volley
MAX_BALL_SPEED = 900.0  # max terminal speed
MAX_BOUNCE_ANGLE = math.radians(60.0)  # maximum reflection angle (degrees)

# Color Themes (70s CRT aesthetics)
THEMES = [
    {
        "name": "CLASSIC B&W (1972)",
        "bg": (12, 12, 12),
        "fg": (235, 235, 235),
        "accent": (130, 130, 130),
        "glow": (255, 255, 255),
    },
    {
        "name": "PHOSPHOR GREEN (P1)",
        "bg": (6, 20, 10),
        "fg": (50, 255, 75),
        "accent": (22, 115, 42),
        "glow": (140, 255, 160),
    },
    {
        "name": "AMBER CRT (P3)",
        "bg": (22, 11, 3),
        "fg": (255, 175, 25),
        "accent": (130, 80, 15),
        "glow": (255, 220, 95),
    },
    {
        "name": "CYAN ARCADE",
        "bg": (4, 15, 26),
        "fg": (35, 235, 255),
        "accent": (18, 95, 130),
        "glow": (165, 245, 255),
    },
]


# ---------------------------------------------------------
# PROCEDURAL 8-BIT AUDIO SYNTHESIZER
# ---------------------------------------------------------
class RetroSoundEngine:
    """Generates authentic 1970s square-wave beeps using NumPy & Pygame."""

    def __init__(self) -> None:
        self.enabled = False
        self.muted = False
        self.paddle_sound: pygame.mixer.Sound | None = None
        self.wall_sound: pygame.mixer.Sound | None = None
        self.score_sound: pygame.mixer.Sound | None = None
        self.win_sound: pygame.mixer.Sound | None = None

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._generate_sounds()
            self.enabled = True
        except Exception:
            # Graceful fallback on machines without active audio device
            self.enabled = False

    def _generate_sounds(self) -> None:
        import numpy as np

        sr = 44100

        def create_square_wave(freq: float, duration: float, vol: float = 0.28) -> pygame.mixer.Sound:
            n_samples = int(sr * duration)
            t = np.linspace(0, duration, n_samples, endpoint=False)
            wave = np.where(np.sin(2 * np.pi * freq * t) >= 0, 1.0, -1.0)
            fade_len = min(int(sr * 0.005), n_samples // 4)
            if fade_len > 0:
                wave[:fade_len] *= np.linspace(0, 1, fade_len)
                wave[-fade_len:] *= np.linspace(1, 0, fade_len)
            samples = (wave * vol * 32767).astype(np.int16)
            stereo = np.ascontiguousarray(np.column_stack((samples, samples)))
            return pygame.sndarray.make_sound(stereo)

        def create_frequency_slide(f_start: float, f_end: float, duration: float, vol: float = 0.28) -> pygame.mixer.Sound:
            n_samples = int(sr * duration)
            freqs = np.linspace(f_start, f_end, n_samples)
            phase = 2 * np.pi * np.cumsum(freqs) / sr
            wave = np.where(np.sin(phase) >= 0, 1.0, -1.0)
            fade_len = min(int(sr * 0.01), n_samples // 4)
            if fade_len > 0:
                wave[:fade_len] *= np.linspace(0, 1, fade_len)
                wave[-fade_len:] *= np.linspace(1, 0, fade_len)
            samples = (wave * vol * 32767).astype(np.int16)
            stereo = np.ascontiguousarray(np.column_stack((samples, samples)))
            return pygame.sndarray.make_sound(stereo)

        def create_arpeggio(notes: List[float], note_duration: float, vol: float = 0.22) -> pygame.mixer.Sound:
            sample_list = []
            for freq in notes:
                n = int(sr * note_duration)
                t = np.linspace(0, note_duration, n, endpoint=False)
                wave = np.where(np.sin(2 * np.pi * freq * t) >= 0, 1.0, -1.0)
                fade_len = min(int(sr * 0.005), n // 4)
                if fade_len > 0:
                    wave[:fade_len] *= np.linspace(0, 1, fade_len)
                    wave[-fade_len:] *= np.linspace(1, 0, fade_len)
                sample_list.append((wave * vol * 32767).astype(np.int16))
            combined = np.concatenate(sample_list)
            stereo = np.ascontiguousarray(np.column_stack((combined, combined)))
            return pygame.sndarray.make_sound(stereo)

        # 1972 Pong arcade sound frequencies:
        self.paddle_sound = create_square_wave(459.0, 0.055, vol=0.25)
        self.wall_sound = create_square_wave(226.0, 0.045, vol=0.22)
        self.score_sound = create_frequency_slide(330.0, 110.0, 0.25, vol=0.30)
        self.win_sound = create_arpeggio([523.25, 659.25, 783.99, 1046.50], 0.12, vol=0.25)

    def play_paddle(self) -> None:
        if self.enabled and not self.muted and self.paddle_sound:
            self.paddle_sound.play()

    def play_wall(self) -> None:
        if self.enabled and not self.muted and self.wall_sound:
            self.wall_sound.play()

    def play_score(self) -> None:
        if self.enabled and not self.muted and self.score_sound:
            self.score_sound.play()

    def play_win(self) -> None:
        if self.enabled and not self.muted and self.win_sound:
            self.win_sound.play()

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted


# ---------------------------------------------------------
# RETRO 7-SEGMENT & PIXEL DRAWING UTILITIES
# ---------------------------------------------------------
class RetroRenderer:
    """Renders chunky 70s-style 7-segment digital displays and CRT overlays."""

    # 7-segment encoding: (a, b, c, d, e, f, g)
    DIGITS = {
        0: (True, True, True, True, True, True, False),
        1: (False, True, True, False, False, False, False),
        2: (True, True, False, True, True, False, True),
        3: (True, True, True, True, False, False, True),
        4: (False, True, True, False, False, True, True),
        5: (True, False, True, True, False, True, True),
        6: (True, False, True, True, True, True, True),
        7: (True, True, True, False, False, False, False),
        8: (True, True, True, True, True, True, True),
        9: (True, True, True, True, False, True, True),
    }

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.scanline_surface = self._build_scanlines(width, height)
        self.vignette_surface = self._build_vignette(width, height)

    def _build_scanlines(self, width: int, height: int) -> pygame.Surface:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(0, height, 3):
            pygame.draw.line(surf, (0, 0, 0, 80), (0, y), (width, y), 1)
        return surf

    def _build_vignette(self, width: int, height: int) -> pygame.Surface:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        border_thickness = 10
        for i in range(border_thickness):
            alpha = int(120 * (1.0 - i / border_thickness))
            rect = pygame.Rect(i, i, width - 2 * i, height - 2 * i)
            pygame.draw.rect(surf, (0, 0, 0, alpha), rect, 1)
        return surf

    def draw_digit(
        self,
        surface: pygame.Surface,
        digit: int,
        x: int,
        y: int,
        w: int = 50,
        h: int = 80,
        thickness: int = 10,
        color: Tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        if digit not in self.DIGITS:
            return

        a, b, c, d, e, f, g = self.DIGITS[digit]
        half_h = h // 2

        if a:
            pygame.draw.rect(surface, color, (x + thickness, y, w - 2 * thickness, thickness))
        if b:
            pygame.draw.rect(surface, color, (x + w - thickness, y + thickness, thickness, half_h - thickness))
        if c:
            pygame.draw.rect(surface, color, (x + w - thickness, y + half_h, thickness, half_h - thickness))
        if d:
            pygame.draw.rect(surface, color, (x + thickness, y + h - thickness, w - 2 * thickness, thickness))
        if e:
            pygame.draw.rect(surface, color, (x, y + half_h, thickness, half_h - thickness))
        if f:
            pygame.draw.rect(surface, color, (x, y + thickness, thickness, half_h - thickness))
        if g:
            pygame.draw.rect(surface, color, (x + thickness, y + half_h - thickness // 2, w - 2 * thickness, thickness))

    def draw_score(
        self,
        surface: pygame.Surface,
        score: int,
        center_x: int,
        top_y: int,
        color: Tuple[int, int, int],
    ) -> None:
        score_str = str(min(score, 99))
        digit_w, digit_h = 44, 76
        spacing = 16
        total_w = len(score_str) * digit_w + (len(score_str) - 1) * spacing
        start_x = center_x - total_w // 2

        for i, char in enumerate(score_str):
            dx = start_x + i * (digit_w + spacing)
            self.draw_digit(surface, int(char), dx, top_y, w=digit_w, h=digit_h, thickness=9, color=color)

    def draw_crt_overlays(self, surface: pygame.Surface, scanlines_enabled: bool) -> None:
        if scanlines_enabled:
            surface.blit(self.scanline_surface, (0, 0))
        surface.blit(self.vignette_surface, (0, 0))


# ---------------------------------------------------------
# GAME CONFIG & ENTITIES
# ---------------------------------------------------------
class GameMode:
    SINGLE_PLAYER = 1  # Player vs CPU
    TWO_PLAYERS = 2  # Player 1 vs Player 2
    ATTRACT = 3  # Demo CPU vs CPU


class Difficulty:
    EASY = 0
    CLASSIC_1972 = 1
    HARD = 2

    NAMES = ["EASY", "CLASSIC 1972", "PRO HARD"]
    SPEED_FACTORS = [0.65, 0.88, 1.15]
    DEADZONES = [36.0, 16.0, 5.0]


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    speed: float
    trail: deque[Tuple[float, float]]

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), BALL_SIZE, BALL_SIZE)


class PongGame:
    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("PONG (1972) - Authentic Retro Arcade")

        self.clock = pygame.time.Clock()
        self.audio = RetroSoundEngine()
        self.renderer = RetroRenderer(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Fonts (Monospace pixel style)
        self.font_large = pygame.font.SysFont("monospace", 36, bold=True)
        self.font_medium = pygame.font.SysFont("monospace", 21, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 14, bold=False)

        # Game Settings
        self.theme_idx = 0
        self.scanlines_enabled = True
        self.game_mode = GameMode.SINGLE_PLAYER
        self.difficulty = Difficulty.CLASSIC_1972

        # State management
        self.score_p1 = 0
        self.score_p2 = 0
        self.p1_y = (SCREEN_HEIGHT - PADDLE_HEIGHT) / 2.0
        self.p2_y = (SCREEN_HEIGHT - PADDLE_HEIGHT) / 2.0

        # Ball
        self.ball = Ball(
            x=0,
            y=0,
            vx=0,
            vy=0,
            speed=INITIAL_BALL_SPEED,
            trail=deque(maxlen=7),
        )

        self.state = "MENU"  # "MENU", "PLAYING", "POINT_SCORED", "GAME_OVER", "PAUSED"
        self.state_timer = 0.0
        self.winner_text = ""
        self.screen_flash = 0.0

        self.reset_match()

    @property
    def theme(self) -> dict:
        return THEMES[self.theme_idx]

    def reset_match(self) -> None:
        """Resets scores and centers paddles."""
        self.score_p1 = 0
        self.score_p2 = 0
        self.p1_y = (SCREEN_HEIGHT - PADDLE_HEIGHT) / 2.0
        self.p2_y = (SCREEN_HEIGHT - PADDLE_HEIGHT) / 2.0
        self.reset_ball(serving_to=1 if random.random() < 0.5 else 2)

    def reset_ball(self, serving_to: int) -> None:
        """Positions ball at screen center and directs initial velocity."""
        self.ball.x = (SCREEN_WIDTH - BALL_SIZE) / 2.0
        self.ball.y = (SCREEN_HEIGHT - BALL_SIZE) / 2.0
        self.ball.speed = INITIAL_BALL_SPEED
        self.ball.trail.clear()

        angle = random.uniform(-math.radians(30), math.radians(30))
        direction = 1 if serving_to == 2 else -1

        self.ball.vx = self.ball.speed * math.cos(angle) * direction
        self.ball.vy = self.ball.speed * math.sin(angle)

    def trigger_serve(self) -> None:
        self.state = "PLAYING"

    # -----------------------------------------------------
    # LOGIC UPDATES
    # -----------------------------------------------------
    def update_paddles(self, dt: float, keys: pygame.key.ScancodeWrapper | None) -> None:
        # Player 1 (W / S or CPU in Attract Mode / Menu)
        if self.state == "MENU" or self.game_mode == GameMode.ATTRACT:
            self._update_ai_paddle(1, dt)
        else:
            if keys and keys[pygame.K_w]:
                self.p1_y -= PADDLE_SPEED * dt
            if keys and keys[pygame.K_s]:
                self.p1_y += PADDLE_SPEED * dt

        # Player 2 (Up / Down or AI)
        if self.state != "MENU" and self.game_mode == GameMode.TWO_PLAYERS:
            if keys and keys[pygame.K_UP]:
                self.p2_y -= PADDLE_SPEED * dt
            if keys and keys[pygame.K_DOWN]:
                self.p2_y += PADDLE_SPEED * dt
        else:
            self._update_ai_paddle(2, dt)

        # Clamp paddles within screen bounds
        self.p1_y = max(10, min(SCREEN_HEIGHT - PADDLE_HEIGHT - 10, self.p1_y))
        self.p2_y = max(10, min(SCREEN_HEIGHT - PADDLE_HEIGHT - 10, self.p2_y))

    def _update_ai_paddle(self, paddle_num: int, dt: float) -> None:
        """Authentic 1970s arcade paddle tracking logic."""
        speed_factor = Difficulty.SPEED_FACTORS[self.difficulty]
        deadzone = Difficulty.DEADZONES[self.difficulty]
        ai_speed = PADDLE_SPEED * speed_factor

        paddle_y = self.p1_y if paddle_num == 1 else self.p2_y
        paddle_center = paddle_y + PADDLE_HEIGHT / 2.0

        is_incoming = (self.ball.vx < 0 and paddle_num == 1) or (self.ball.vx > 0 and paddle_num == 2)

        if is_incoming:
            target_y = self.ball.y + BALL_SIZE / 2.0
            diff = target_y - paddle_center

            if abs(diff) > deadzone:
                direction = 1.0 if diff > 0 else -1.0
                step = direction * ai_speed * dt
                if abs(step) > abs(diff):
                    step = diff
                if paddle_num == 1:
                    self.p1_y += step
                else:
                    self.p2_y += step
        else:
            # When ball is heading away, slowly reposition toward center
            target_y = SCREEN_HEIGHT / 2.0
            diff = target_y - paddle_center
            if abs(diff) > 20.0:
                direction = 1.0 if diff > 0 else -1.0
                step = direction * (ai_speed * 0.4) * dt
                if paddle_num == 1:
                    self.p1_y += step
                else:
                    self.p2_y += step

    def update_ball(self, dt: float) -> None:
        self.ball.trail.append((self.ball.x, self.ball.y))

        # Movement step
        self.ball.x += self.ball.vx * dt
        self.ball.y += self.ball.vy * dt

        # Wall collisions (Top & Bottom borders)
        if self.ball.y <= 10:
            self.ball.y = 10
            self.ball.vy = abs(self.ball.vy)
            if self.state != "MENU":
                self.audio.play_wall()
        elif self.ball.y + BALL_SIZE >= SCREEN_HEIGHT - 10:
            self.ball.y = SCREEN_HEIGHT - 10 - BALL_SIZE
            self.ball.vy = -abs(self.ball.vy)
            if self.state != "MENU":
                self.audio.play_wall()

        # Paddle Rectangles
        p1_rect = pygame.Rect(30, int(self.p1_y), PADDLE_WIDTH, PADDLE_HEIGHT)
        p2_rect = pygame.Rect(SCREEN_WIDTH - 30 - PADDLE_WIDTH, int(self.p2_y), PADDLE_WIDTH, PADDLE_HEIGHT)
        ball_rect = self.ball.rect

        # Left Paddle Collision
        if self.ball.vx < 0 and ball_rect.colliderect(p1_rect):
            self._handle_paddle_bounce(p1_rect, is_left=True)

        # Right Paddle Collision
        elif self.ball.vx > 0 and ball_rect.colliderect(p2_rect):
            self._handle_paddle_bounce(p2_rect, is_left=False)

        # Scoring Condition
        if self.ball.x + BALL_SIZE < 0:
            self._handle_score(scorer=2)
        elif self.ball.x > SCREEN_WIDTH:
            self._handle_score(scorer=1)

    def _handle_paddle_bounce(self, paddle_rect: pygame.Rect, is_left: bool) -> None:
        """Calculates authentic 1970s angular bounce and speeds up ball."""
        if is_left:
            self.ball.x = paddle_rect.right
        else:
            self.ball.x = paddle_rect.left - BALL_SIZE

        # Normalized offset from -1.0 (top) to +1.0 (bottom)
        ball_center = self.ball.y + BALL_SIZE / 2.0
        paddle_center = paddle_rect.y + paddle_rect.height / 2.0
        norm_offset = (ball_center - paddle_center) / (paddle_rect.height / 2.0)
        norm_offset = max(-1.0, min(1.0, norm_offset))

        # Speed up volley
        self.ball.speed = min(MAX_BALL_SPEED, self.ball.speed * SPEED_INCREMENT)

        # Angular deflection
        bounce_angle = norm_offset * MAX_BOUNCE_ANGLE
        dir_x = 1.0 if is_left else -1.0

        self.ball.vx = self.ball.speed * math.cos(bounce_angle) * dir_x
        self.ball.vy = self.ball.speed * math.sin(bounce_angle)

        if self.state != "MENU":
            self.audio.play_paddle()

    def _handle_score(self, scorer: int) -> None:
        if self.state == "MENU":
            # In Menu / Attract demo, loop continuously
            self.reset_ball(serving_to=1 if scorer == 2 else 2)
            return

        self.screen_flash = 0.25
        self.audio.play_score()

        if scorer == 1:
            self.score_p1 += 1
        else:
            self.score_p2 += 1

        if self.score_p1 >= WINNING_SCORE or self.score_p2 >= WINNING_SCORE:
            if self.game_mode == GameMode.SINGLE_PLAYER:
                self.winner_text = "PLAYER 1 WINS!" if self.score_p1 >= WINNING_SCORE else "COMPUTER WINS!"
            elif self.game_mode == GameMode.TWO_PLAYERS:
                self.winner_text = "PLAYER 1 WINS!" if self.score_p1 >= WINNING_SCORE else "PLAYER 2 WINS!"
            else:
                self.winner_text = "CPU 1 WINS!" if self.score_p1 >= WINNING_SCORE else "CPU 2 WINS!"

            self.state = "GAME_OVER"
            self.audio.play_win()
        else:
            self.state = "POINT_SCORED"
            self.state_timer = 0.95
            self.reset_ball(serving_to=1 if scorer == 2 else 2)

    # -----------------------------------------------------
    # RENDERING
    # -----------------------------------------------------
    def render(self) -> None:
        theme = self.theme
        bg_col = theme["bg"]
        fg_col = theme["fg"]
        accent_col = theme["accent"]
        glow_col = theme["glow"]

        self.screen.fill(bg_col)

        # Point scored screen flash
        if self.screen_flash > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash_surf.fill(fg_col)
            flash_surf.set_alpha(int(self.screen_flash * 90))
            self.screen.blit(flash_surf, (0, 0))

        # Court borders
        border_thickness = 8
        pygame.draw.rect(self.screen, fg_col, (0, 0, SCREEN_WIDTH, border_thickness))
        pygame.draw.rect(self.screen, fg_col, (0, SCREEN_HEIGHT - border_thickness, SCREEN_WIDTH, border_thickness))

        # Center dashed net
        net_w = 6
        net_h = 16
        net_gap = 14
        net_x = (SCREEN_WIDTH - net_w) // 2
        for y in range(border_thickness + 6, SCREEN_HEIGHT - border_thickness, net_h + net_gap):
            pygame.draw.rect(self.screen, accent_col, (net_x, y, net_w, net_h))

        # Scores
        self.renderer.draw_score(self.screen, self.score_p1, center_x=SCREEN_WIDTH // 4, top_y=35, color=fg_col)
        self.renderer.draw_score(self.screen, self.score_p2, center_x=3 * SCREEN_WIDTH // 4, top_y=35, color=fg_col)

        # Paddles
        p1_rect = pygame.Rect(30, int(self.p1_y), PADDLE_WIDTH, PADDLE_HEIGHT)
        p2_rect = pygame.Rect(SCREEN_WIDTH - 30 - PADDLE_WIDTH, int(self.p2_y), PADDLE_WIDTH, PADDLE_HEIGHT)
        pygame.draw.rect(self.screen, fg_col, p1_rect)
        pygame.draw.rect(self.screen, fg_col, p2_rect)

        # Ball and Phosphor Trail
        trail_len = len(self.ball.trail)
        for i, (tx, ty) in enumerate(self.ball.trail):
            alpha = int(70 * (i + 1) / (trail_len + 1))
            trail_surf = pygame.Surface((BALL_SIZE, BALL_SIZE), pygame.SRCALPHA)
            trail_surf.fill((*glow_col, alpha))
            self.screen.blit(trail_surf, (int(tx), int(ty)))

        pygame.draw.rect(self.screen, fg_col, self.ball.rect)

        # State overlays
        if self.state == "MENU":
            self._render_menu(fg_col, accent_col, bg_col)
        elif self.state == "PAUSED":
            self._render_paused(fg_col, bg_col)
        elif self.state == "GAME_OVER":
            self._render_game_over(fg_col, bg_col)
        elif self.state == "POINT_SCORED":
            msg = self.font_medium.render("READY", True, fg_col)
            self.screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT // 2 - 40))

        # Status Footer
        self._render_hud_bar(accent_col)

        # Apply CRT Scanlines & Screen Vignette
        self.renderer.draw_crt_overlays(self.screen, self.scanlines_enabled)

        pygame.display.flip()

    def _render_menu(self, fg_col: Tuple[int, int, int], accent_col: Tuple[int, int, int], bg_col: Tuple[int, int, int]) -> None:
        # Dim background overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*bg_col, 205))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("P  O  N  G", True, fg_col)
        sub = self.font_medium.render("1972 RETRO ARCADE", True, accent_col)

        m1 = self.font_medium.render("[1] 1 PLAYER  (VS COMPUTER)", True, fg_col if self.game_mode == GameMode.SINGLE_PLAYER else accent_col)
        m2 = self.font_medium.render("[2] 2 PLAYERS (LOCAL: W/S vs UP/DOWN)", True, fg_col if self.game_mode == GameMode.TWO_PLAYERS else accent_col)
        ma = self.font_medium.render("[A] ATTRACT MODE (CPU vs CPU)", True, fg_col if self.game_mode == GameMode.ATTRACT else accent_col)

        start = self.font_medium.render(">> PRESS SPACE TO SERVE <<", True, fg_col)

        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 130))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 180))
        self.screen.blit(m1, (SCREEN_WIDTH // 2 - m1.get_width() // 2, 255))
        self.screen.blit(m2, (SCREEN_WIDTH // 2 - m2.get_width() // 2, 295))
        self.screen.blit(ma, (SCREEN_WIDTH // 2 - ma.get_width() // 2, 335))
        self.screen.blit(start, (SCREEN_WIDTH // 2 - start.get_width() // 2, 415))

    def _render_paused(self, fg_col: Tuple[int, int, int], bg_col: Tuple[int, int, int]) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*bg_col, 190))
        self.screen.blit(overlay, (0, 0))

        pause_txt = self.font_large.render("- PAUSED -", True, fg_col)
        hint = self.font_medium.render("PRESS P OR SPACE TO RESUME", True, fg_col)
        esc_hint = self.font_small.render("ESC: TITLE MENU   |   R: RESTART MATCH", True, fg_col)

        self.screen.blit(pause_txt, (SCREEN_WIDTH // 2 - pause_txt.get_width() // 2, 230))
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 290))
        self.screen.blit(esc_hint, (SCREEN_WIDTH // 2 - esc_hint.get_width() // 2, 340))

    def _render_game_over(self, fg_col: Tuple[int, int, int], bg_col: Tuple[int, int, int]) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*bg_col, 205))
        self.screen.blit(overlay, (0, 0))

        win_txt = self.font_large.render(self.winner_text, True, fg_col)
        hint = self.font_medium.render("PRESS SPACE FOR REMATCH", True, fg_col)
        menu_hint = self.font_small.render("PRESS ESC TO RETURN TO MENU", True, fg_col)

        self.screen.blit(win_txt, (SCREEN_WIDTH // 2 - win_txt.get_width() // 2, 230))
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 290))
        self.screen.blit(menu_hint, (SCREEN_WIDTH // 2 - menu_hint.get_width() // 2, 340))

    def _render_hud_bar(self, col: Tuple[int, int, int]) -> None:
        snd_str = "MUTED" if self.audio.muted else "SOUND ON"
        scan_str = "CRT SCANLINES ON" if self.scanlines_enabled else "SCANLINES OFF"
        diff_str = Difficulty.NAMES[self.difficulty]
        bar_text = f"[C] THEME: {self.theme['name']}   |   [D] CPU: {diff_str}   |   [L] {scan_str}   |   [M] {snd_str}"
        surf = self.font_small.render(bar_text, True, col)
        self.screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, SCREEN_HEIGHT - 24))

    # -----------------------------------------------------
    # MAIN LOOP
    # -----------------------------------------------------
    def run(self) -> None:
        running = True

        while running:
            dt = self.clock.tick(60) / 1000.0
            if dt > 0.05:
                dt = 0.05

            if self.screen_flash > 0:
                self.screen_flash = max(0.0, self.screen_flash - dt * 2.5)

            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state in ("PLAYING", "PAUSED", "GAME_OVER"):
                            self.state = "MENU"
                        elif self.state == "MENU":
                            running = False

                    elif event.key == pygame.K_SPACE:
                        if self.state == "MENU":
                            self.reset_match()
                            self.state = "PLAYING"
                        elif self.state == "PLAYING":
                            self.state = "PAUSED"
                        elif self.state == "PAUSED":
                            self.state = "PLAYING"
                        elif self.state == "GAME_OVER":
                            self.reset_match()
                            self.state = "PLAYING"

                    elif event.key == pygame.K_p:
                        if self.state == "PLAYING":
                            self.state = "PAUSED"
                        elif self.state == "PAUSED":
                            self.state = "PLAYING"

                    elif event.key == pygame.K_r:
                        self.reset_match()
                        self.state = "PLAYING"

                    # Color theme cycle
                    elif event.key == pygame.K_c:
                        self.theme_idx = (self.theme_idx + 1) % len(THEMES)

                    # Scanlines toggle ('L' for scanlines)
                    elif event.key == pygame.K_l:
                        self.scanlines_enabled = not self.scanlines_enabled

                    # Mute toggle
                    elif event.key == pygame.K_m:
                        self.audio.toggle_mute()

                    # Difficulty toggle
                    elif event.key == pygame.K_d:
                        self.difficulty = (self.difficulty + 1) % 3

                    # Mode keys
                    elif event.key == pygame.K_1:
                        self.game_mode = GameMode.SINGLE_PLAYER
                        if self.state == "MENU":
                            self.reset_match()
                            self.state = "PLAYING"
                    elif event.key == pygame.K_2:
                        self.game_mode = GameMode.TWO_PLAYERS
                        if self.state == "MENU":
                            self.reset_match()
                            self.state = "PLAYING"
                    elif event.key == pygame.K_a:
                        self.game_mode = GameMode.ATTRACT
                        if self.state == "MENU":
                            self.reset_match()
                            self.state = "PLAYING"

            keys = pygame.key.get_pressed()

            if self.state == "PLAYING":
                self.update_paddles(dt, keys)
                self.update_ball(dt)

            elif self.state == "POINT_SCORED":
                self.update_paddles(dt, keys)
                self.state_timer -= dt
                if self.state_timer <= 0:
                    self.state = "PLAYING"

            elif self.state == "MENU":
                # Background demo attract mode
                self.update_paddles(dt, None)
                self.update_ball(dt)

            self.render()

        pygame.quit()
        sys.exit()


def main() -> None:
    game = PongGame()
    game.run()


if __name__ == "__main__":
    main()
