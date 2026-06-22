import pygame
import os


class Soldier:       

    def __init__(self, start: tuple[float, float], end: tuple[float, float],
                delay: float, color: tuple[int, int, int]):
        
        self.x, self.y = start
        self.end = end
        self.delay = delay
        self.color = color
        self.arrived = False
 
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = (dx ** 2 + dy ** 2) ** 0.5 or 1
        self.vx = dx / dist * 180
        self.vy = dy / dist * 180
 
    def update(self, dt: float) -> None:
        if self.arrived:
            return
        if self.delay > 0:
            self.delay -= dt
            return
 
        self.x += self.vx * dt
        self.y += self.vy * dt
 
        if ((self.end[0] - self.x) ** 2 + (self.end[1] - self.y) ** 2) ** 0.5 < 5:
            self.x, self.y = self.end
            self.arrived = True
 
    def draw(self, screen: pygame.Surface) -> None:
        if self.delay > 0 or self.arrived:
            return
        pos = (int(self.x), int(self.y))
        pygame.draw.circle(screen, self.color, pos,5)
        pygame.draw.circle(screen, (20, 20, 20), pos, 5, 2)


class Explosion:
    frames: list[pygame.Surface] = []

    @classmethod
    def load_frames(cls, folder: str) -> None:
        cls.frames = []

        files = sorted(os.listdir(folder))

        for file in files:
            img = pygame.image.load(
                os.path.join(folder, file)
            ).convert_alpha()

            img = pygame.transform.scale(img, (500, 500))

            cls.frames.append(img)

    def __init__(self, pos: tuple[float, float]) -> None:
        self.x, self.y = pos

        self.frame_index = 0
        self.timer = 0

        self.frame_duration = 0.05
        self.done = False

    def update(self, dt: float) -> None:
        self.timer += dt

        if self.timer >= self.frame_duration:
            self.timer = 0
            self.frame_index += 1

            if self.frame_index >= len(self.frames):
                self.done = True

    def draw(self, screen: pygame.Surface) -> None:
        if self.done:
            return

        frame = self.frames[self.frame_index]

        rect = frame.get_rect(center=(self.x, self.y))
        screen.blit(frame, rect)