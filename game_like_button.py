import pygame
import sys
import math

pygame.init()

# --- Window Setup ---
WIDTH, HEIGHT = 480, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pause Menu")
clock = pygame.time.Clock()

# --- Colors ---
BG_COLOR       = (139, 90, 43)       # dark wood brown background
PANEL_BG       = (255, 245, 220)     # creamy beige panel
PANEL_BORDER   = (100, 180, 255)     # blue border
TITLE_BG       = (255, 245, 220)
TITLE_TEXT     = (80, 120, 200)      # blue text
SLIDER_TRACK   = (210, 190, 160)     # tan track
SLIDER_FILL    = (255, 220, 0)       # yellow fill
SLIDER_THUMB   = (80, 150, 255)      # blue thumb
TOGGLE_ON_BG   = (80, 220, 120)      # green when ON
TOGGLE_OFF_BG  = (180, 180, 180)
TOGGLE_THUMB   = (255, 255, 255)
BTN_SUPPORT    = (80, 150, 255)      # blue support button
BTN_HOME       = (230, 90, 60)       # orange/red home
BTN_RESUME     = (50, 200, 120)      # green resume
CLOSE_BTN      = (230, 70, 70)       # red X button
TEXT_WHITE     = (255, 255, 255)
TEXT_BROWN     = (160, 100, 60)
ICON_COLOR     = (160, 110, 70)

# --- Fonts ---
font_title  = pygame.font.SysFont("Arial Rounded MT Bold", 36, bold=True)
font_label  = pygame.font.SysFont("Arial Rounded MT Bold", 22, bold=True)
font_btn    = pygame.font.SysFont("Arial Rounded MT Bold", 28, bold=True)
font_icon   = pygame.font.SysFont("Segoe UI Emoji", 26)

# --- State ---
music_val   = 0.75   # 0.0 - 1.0
sound_val   = 0.75
haptics_on  = True
dragging    = None   # 'music' | 'sound'

# --- Layout ---
panel_x, panel_y = 60, 80
panel_w, panel_h = 360, 520
panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

slider_x   = panel_x + 90
slider_w   = 220
slider_h   = 28
music_sy   = panel_y + 120
sound_sy   = panel_y + 185
haptic_sy  = panel_y + 250

toggle_x   = panel_x + 260
toggle_w   = 70
toggle_h   = 34

support_rect = pygame.Rect(panel_x + 50, panel_y + 330, 260, 60)
home_rect    = pygame.Rect(panel_x + 30, panel_y + 420, 70, 60)
resume_rect  = pygame.Rect(panel_x + 120, panel_y + 420, 200, 60)
close_rect   = pygame.Rect(panel_x + panel_w - 28, panel_y - 18, 40, 40)


def draw_rounded_rect(surf, color, rect, radius, border_color=None, border=0):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border_color and border > 0:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_slider(surf, val, sx, sy):
    track = pygame.Rect(sx, sy - slider_h // 2, slider_w, slider_h)
    draw_rounded_rect(surf, SLIDER_TRACK, track, 14)
    fill_w = int(slider_w * val)
    if fill_w > 0:
        fill = pygame.Rect(sx, sy - slider_h // 2, fill_w, slider_h)
        draw_rounded_rect(surf, SLIDER_FILL, fill, 14)
    thumb_x = sx + int(slider_w * val)
    pygame.draw.circle(surf, SLIDER_THUMB, (thumb_x, sy), 20)
    pygame.draw.circle(surf, (255, 255, 255), (thumb_x, sy), 14)


def draw_toggle(surf, on, tx, ty):
    bg = TOGGLE_ON_BG if on else TOGGLE_OFF_BG
    rect = pygame.Rect(tx, ty - toggle_h // 2, toggle_w, toggle_h)
    draw_rounded_rect(surf, bg, rect, 17)
    if on:
        thumb_x = tx + toggle_w - toggle_h // 2 - 4
        label = font_label.render("ON", True, (255, 255, 255))
        surf.blit(label, (tx + 6, ty - 11))
    else:
        thumb_x = tx + toggle_h // 2 + 4
        label = font_label.render("OFF", True, (255, 255, 255))
        surf.blit(label, (tx + 28, ty - 11))
    pygame.draw.circle(surf, TOGGLE_THUMB, (thumb_x, ty), toggle_h // 2 - 3)


def draw_button(surf, rect, color, text, icon=None, radius=30):
    shadow = pygame.Rect(rect.x + 3, rect.y + 5, rect.w, rect.h)
    dark = tuple(max(0, c - 60) for c in color)
    draw_rounded_rect(surf, dark, shadow, radius)
    draw_rounded_rect(surf, color, rect, radius)
    if icon:
        ic = font_icon.render(icon, True, TEXT_WHITE)
        surf.blit(ic, (rect.x + 16, rect.centery - ic.get_height() // 2))
        t = font_btn.render(text, True, TEXT_WHITE)
        surf.blit(t, (rect.x + 55, rect.centery - t.get_height() // 2))
    else:
        t = font_btn.render(text, True, TEXT_WHITE)
        surf.blit(t, (rect.centerx - t.get_width() // 2,
                      rect.centery - t.get_height() // 2))


def draw_note(surf, x, y, color):
    """Draw a simple music note"""
    pygame.draw.circle(surf, color, (x, y + 12), 7)
    pygame.draw.line(surf, color, (x + 6, y + 12), (x + 6, y - 6), 3)
    pygame.draw.line(surf, color, (x + 6, y - 6), (x + 18, y - 2), 3)
    pygame.draw.circle(surf, color, (x + 18, y + 6), 7)
    pygame.draw.line(surf, color, (x + 24, y + 6), (x + 24, y - 12), 3)


def draw_speaker(surf, x, y, color):
    pts = [(x, y - 8), (x + 10, y - 8), (x + 18, y - 16),
           (x + 18, y + 16), (x + 10, y + 8), (x, y + 8)]
    pygame.draw.polygon(surf, color, pts)
    for i, r in enumerate([10, 16, 22]):
        pygame.draw.arc(surf, color,
                        (x + 16, y - r, r * 2, r * 2),
                        -0.8, 0.8, 3)


def draw_vibrate(surf, x, y, color):
    for dx in [-14, -8, 8, 14]:
        pygame.draw.rect(surf, color, (x + dx, y - 10, 4, 20), border_radius=2)
    pygame.draw.rect(surf, color, (x - 4, y - 14, 8, 28), border_radius=4)


def get_slider_val(mx, sx):
    return max(0.0, min(1.0, (mx - sx) / slider_w))


running = True
while running:
    dt = clock.tick(60)
    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Close button
            if close_rect.collidepoint(mx, my):
                running = False

            # Sliders
            music_thumb_x = slider_x + int(slider_w * music_val)
            if abs(mx - music_thumb_x) < 24 and abs(my - music_sy) < 24:
                dragging = 'music'
            sound_thumb_x = slider_x + int(slider_w * sound_val)
            if abs(mx - sound_thumb_x) < 24 and abs(my - sound_sy) < 24:
                dragging = 'sound'

            # Toggle haptics
            tog_rect = pygame.Rect(toggle_x, haptic_sy - toggle_h // 2, toggle_w, toggle_h)
            if tog_rect.collidepoint(mx, my):
                haptics_on = not haptics_on

            # Buttons
            if resume_rect.collidepoint(mx, my):
                print("RESUME clicked")
            if home_rect.collidepoint(mx, my):
                print("HOME clicked")
            if support_rect.collidepoint(mx, my):
                print("SUPPORT clicked")

        elif event.type == pygame.MOUSEBUTTONUP:
            dragging = None

        elif event.type == pygame.MOUSEMOTION:
            if dragging == 'music':
                music_val = get_slider_val(mx, slider_x)
            elif dragging == 'sound':
                sound_val = get_slider_val(mx, slider_x)

    # --- Draw ---
    # Background (simulate game behind)
    screen.fill(BG_COLOR)
    for i in range(0, WIDTH, 40):
        for j in range(0, HEIGHT, 40):
            pygame.draw.rect(screen, (120, 75, 35), (i, j, 38, 38), border_radius=4)

    # Panel shadow
    shadow_rect = pygame.Rect(panel_x + 5, panel_y + 8, panel_w, panel_h)
    draw_rounded_rect(screen, (80, 50, 20), shadow_rect, 30)

    # Panel
    draw_rounded_rect(screen, PANEL_BG, panel_rect, 30, PANEL_BORDER, 6)

    # Title bar
    title_rect = pygame.Rect(panel_x + 50, panel_y - 28, panel_w - 100, 56)
    draw_rounded_rect(screen, PANEL_BG, title_rect, 20, PANEL_BORDER, 5)
    t = font_title.render("PAUSE", True, TITLE_TEXT)
    screen.blit(t, (title_rect.centerx - t.get_width() // 2,
                    title_rect.centery - t.get_height() // 2))

    # Close button
    draw_rounded_rect(screen, CLOSE_BTN, close_rect, 20)
    cx = font_btn.render("✕", True, TEXT_WHITE)
    screen.blit(cx, (close_rect.centerx - cx.get_width() // 2,
                     close_rect.centery - cx.get_height() // 2))

    # Music icon + slider
    draw_note(screen, panel_x + 30, music_sy - 8, ICON_COLOR)
    draw_slider(screen, music_val, slider_x, music_sy)

    # Sound icon + slider
    draw_speaker(screen, panel_x + 22, sound_sy, ICON_COLOR)
    draw_slider(screen, sound_val, slider_x, sound_sy)

    # Haptics icon + label + toggle
    draw_vibrate(screen, panel_x + 38, haptic_sy, ICON_COLOR)
    lbl = font_label.render("HAPTICS", True, TEXT_BROWN)
    screen.blit(lbl, (panel_x + 70, haptic_sy - lbl.get_height() // 2))
    draw_toggle(screen, haptics_on, toggle_x, haptic_sy)

    # Divider
    pygame.draw.line(screen, (210, 190, 160),
                     (panel_x + 20, panel_y + 300),
                     (panel_x + panel_w - 20, panel_y + 300), 2)

    # Support button
    draw_button(screen, support_rect, BTN_SUPPORT, "SUPPORT", icon="🎧")

    # Home button
    draw_button(screen, home_rect, BTN_HOME, "⌂", radius=35)

    # Resume button
    draw_button(screen, resume_rect, BTN_RESUME, "RESUME", radius=35)

    pygame.display.flip()

pygame.quit()
sys.exit()