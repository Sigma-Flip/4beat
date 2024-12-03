import pygame
import sys
import random
import librosa
import time
from collections import deque
import os

class Note:
    def __init__(self, time, track, duration=0):
        self.time = time  # 노트가 생성될 시간 (초)
        self.track = track  # 트랙 위치
        self.duration = duration  # 롱 노트의 지속 시간 (0이면 일반 노트)
        self.hit = False  # 처리 여부
        self.hold = False  # 롱 노트의 경우, 현재 눌리고 있는지 여부

class RhythmGame:
    def __init__(self, audio_file, difficulty="Normal"):
        pygame.init()

        # 화면 설정
        self.h, self.w = 800, 900
        self.screen = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption("Stylish Rhythm Game")

        # 텍스트 설정
        self.font = pygame.font.SysFont("Courier", 24, True, True)
        self.text_color = (255, 255, 255)

        # 난이도 설정
        self.difficulty = difficulty
        self.note_speed, self.additional_notes = self._set_difficulty(difficulty)

        # 음악 및 노트 스케줄링
        self.audio_file = audio_file
        self.notes = []  # 배열로 노트 관리
        self._load_audio()

        # 입력 관리
        self.input_queue = deque()  # 입력 기록 큐
        self.keys_pressed = [False, False, False, False]  # 각 키의 누름 상태 (LEFT, DOWN, UP, RIGHT)

        # 판정 시스템
        self.judgment_ranges = {
            "Perfect": 0.05,
            "Great": 0.1,
            "Good": 0.2,
            "Bad": 0.3,
            "Miss": float("inf")
        }

        # 스코어 및 콤보 관리
        self.score_stack = []  # 스코어 스택
        self.combo_queue = deque()  # 콤보 큐
        self.score = 0
        self.combo = 0
        self.max_combo = 0  # 최대 콤보를 저장하기 위한 변수

        # 판정 표시용 텍스트 관리
        self.judgment_texts = []

        # 게임 실행 플래그
        self.running = True

        # 이미지 로드
        self.image = pygame.image.load(os.path.join(os.path.dirname(__file__), 'images.jpeg'))
        self.image = pygame.transform.scale(self.image, (300, 200))  # 이미지 크기 조정

    def _set_difficulty(self, difficulty):
        """난이도에 따라 노트 속도와 추가 노트 양 설정"""
        if difficulty == "Easy":
            return 200, 1  # 속도 줄이고 추가 노트 적게
        elif difficulty == "Normal":
            return 300, 2  # 기본 속도와 기본 추가 노트
        elif difficulty == "Hard":
            return 400, 3  # 속도 빠르게, 추가 노트 많이
        else:
            raise ValueError("Unknown difficulty level")

    def _load_audio(self):
        """음악 파일 로드 및 노트 생성"""
        pygame.mixer.init()
        pygame.mixer.music.load(self.audio_file)

        # librosa를 통해 비트 감지
        y, sr = librosa.load(self.audio_file, sr=None)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        # 노트를 배열로 관리 (난이도에 따라 추가 노트를 생성하여 조절)
        for i in range(len(beat_times)):
            track = random.randint(0, 3)  # 트랙 번호 (0, 1, 2, 3 중 랜덤 선택)
            if random.random() > 0.7:  # 일부 노트를 롱 노트로 설정
                duration = random.uniform(0.5, 1.5)  # 롱 노트의 지속 시간 (0.5초 ~ 1.5초)
            else:
                duration = 0
            self.notes.append(Note(time=beat_times[i], track=track, duration=duration))

        for _ in range(self.additional_notes):
            for i in range(len(beat_times)):
                track = random.randint(0, 3)
                additional_time = beat_times[i] + random.uniform(0.1, 0.5)
                if random.random() > 0.7:  # 일부 노트를 롱 노트로 설정
                    duration = random.uniform(0.5, 1.5)  # 롱 노트의 지속 시간
                else:
                    duration = 0
                self.notes.append(Note(time=additional_time, track=track, duration=duration))

    def _judge_input(self, note, input_time):
        """입력 타이밍과 판정"""
        if note.hit:
            return "Miss"
        
        timing_diff = abs(note.time - input_time)
        for judgment, threshold in self.judgment_ranges.items():
            if timing_diff <= threshold:
                note.hit = True
                self.judgment_texts.append((judgment, time.time(), note.track))  # 판정 텍스트 추가
                return judgment
        return "Miss"

    def _process_notes(self, input_time, track):
        """입력된 타이밍과 트랙을 기반으로 가장 가까운 노트 하나만 업데이트"""
        closest_note = None
        min_diff = float('inf')

        # 현재 트랙에서 가장 가까운 노트 찾기
        for note in self.notes:
            if not note.hit and note.track == track:
                timing_diff = abs(note.time - input_time)
                if timing_diff < min_diff:
                    closest_note = note
                    min_diff = timing_diff

        # 가장 가까운 노트가 있고, 판정 범위 내에 들어올 경우에만 처리
        if closest_note and min_diff <= self.judgment_ranges["Bad"]:
            if closest_note.duration == 0:
                # 일반 노트 처리
                judgment = self._judge_input(closest_note, input_time)
                if judgment != "Miss":
                    self._update_score_and_combo(judgment)
            else:
                # 롱 노트 시작 처리
                if not closest_note.hold:
                    judgment = self._judge_input(closest_note, input_time)
                    if judgment != "Miss":
                        closest_note.hold = True

    def _update_score_and_combo(self, judgment):
        """판정에 따라 점수와 콤보 업데이트"""
        scores = {"Perfect": 300, "Great": 200, "Good": 100, "Bad": -100, "Miss": 0}
        self.score_stack.append(scores[judgment])
        self.score += scores[judgment]

        if judgment in ["Miss", "Bad"]:
            self.combo_queue.clear()
        else:
            self.combo_queue.append(1)

        self.combo = len(self.combo_queue)
        if self.combo > self.max_combo:
            self.max_combo = self.combo

    def run(self):
        """게임 실행"""
        pygame.mixer.music.play()
        clock = pygame.time.Clock()

        while self.running:
            self.screen.fill((30, 30, 30))  # 배경 색상 변경 (더 어두운 톤으로)

            # 이미지 삽입 (화면 중앙에)
            self.screen.blit(self.image, (self.w // 2 - self.image.get_width() // 2, self.h // 2 - self.image.get_height() // 2))

            # 입력 이벤트 처리
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.KEYDOWN:
                    input_time = pygame.mixer.music.get_pos() / 1000.0  # 현재 재생 시간 (초)
                    if event.key == pygame.K_LEFT:
                        self.input_queue.append((input_time, 0))  # 왼쪽 트랙 입력
                        self.keys_pressed[0] = True
                    if event.key == pygame.K_DOWN:
                        self.input_queue.append((input_time, 1))  # 아래쪽 트랙 입력
                        self.keys_pressed[1] = True
                    if event.key == pygame.K_UP:
                        self.input_queue.append((input_time, 2))  # 위쪽 트랙 입력
                        self.keys_pressed[2] = True
                    if event.key == pygame.K_RIGHT:
                        self.input_queue.append((input_time, 3))  # 오른쪽 트랙 입력
                        self.keys_pressed[3] = True
                    if event.key == pygame.K_q:
                        self.running = False  # Q 키를 누르면 게임 종료

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_LEFT:
                        self.keys_pressed[0] = False
                    if event.key == pygame.K_DOWN:
                        self.keys_pressed[1] = False
                    if event.key == pygame.K_UP:
                        self.keys_pressed[2] = False
                    if event.key == pygame.K_RIGHT:
                        self.keys_pressed[3] = False

            # 입력 처리
            if self.input_queue:
                input_time, track = self.input_queue.popleft()
                self._process_notes(input_time, track)

            # 노트 그리기
            current_time = pygame.mixer.music.get_pos() / 1000.0  # 현재 재생 시간 (초)
            for note in self.notes:
                if not note.hit or (note.duration > 0 and note.hold):
                    x = 200 + note.track * 150  # 트랙에 따른 x 위치
                    y = int((note.time - current_time) * self.note_speed)  # y 위치 계산 (위에서 아래로 내려오도록 설정)
                    y = self.h - y  # y 값을 반전시켜 노트가 위에서 아래로 떨어지게 설정
                    if y > self.h:
                        note.hit = True  # 화면 밖으로 벗어나면 Miss 처리
                    else:
                        if note.duration == 0:
                            # 일반 노트 그리기
                            pygame.draw.rect(self.screen, (0, 200, 255), (x, y, 50, 15), border_radius=10)
                        else:
                            # 롱 노트 그리기
                            end_y = y - int(note.duration * self.note_speed)
                            pygame.draw.rect(self.screen, (0, 150, 255), (x, min(y, self.h), 50, max(15, y - end_y)), border_radius=10)

            # 4키 라인 그리기
            for i in range(4):
                x = 200 + i * 150
                color = (100, 100, 100) if not self.keys_pressed[i] else (50, 205, 50)  # 키를 누르면 녹색으로 변경
                pygame.draw.rect(self.screen, color, (x, self.h - 50, 50, 50), border_radius=10)  # 키 표시

            # 점수 및 콤보 표시
            score_text = self.font.render(f"Score: {self.score}", True, self.text_color)
            combo_text = self.font.render(f"Combo: {self.combo}", True, self.text_color)
            self.screen.blit(score_text, (10, 10))
            self.screen.blit(combo_text, (10, 40))

            # 판정 텍스트 표시
            current_time = time.time()
            for judgment, timestamp, track in self.judgment_texts[:]:
                if current_time - timestamp < 1:  # 판정 텍스트를 1초 동안 화면에 표시
                    x = 200 + track * 150
                    color = {"Perfect": (255, 215, 0), "Great": (0, 255, 0), "Good": (0, 0, 255), "Bad": (255, 0, 0)}
                    judgment_text = self.font.render(judgment, True, color.get(judgment, (255, 255, 0)))
                    self.screen.blit(judgment_text, (x, self.h - 120))  # 각 트랙의 바로 위에 판정 텍스트 표시
                else:
                    self.judgment_texts.remove((judgment, timestamp, track))

            # 화면 업데이트
            pygame.display.flip()
            clock.tick(60)

        self._show_end_screen()

    def _show_end_screen(self):
        """게임 종료 후 결과 화면 표시"""
        self.screen.fill((0, 0, 0))  # 화면을 검은색으로 채움
        end_text = self.font.render("Game Over", True, (255, 0, 0))
        score_text = self.font.render(f"Final Score: {self.score}", True, (255, 255, 255))
        max_combo_text = self.font.render(f"Max Combo: {self.max_combo}", True, (255, 255, 255))

        self.screen.blit(end_text, (self.w // 2 - end_text.get_width() // 2, self.h // 2 - 100))
        self.screen.blit(score_text, (self.w // 2 - score_text.get_width() // 2, self.h // 2))
        self.screen.blit(max_combo_text, (self.w // 2 - max_combo_text.get_width() // 2, self.h // 2 + 50))

        pygame.display.flip()

        # 종료 화면을 일정 시간 유지하고 대기
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    waiting = False

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = RhythmGame("/Users/dongwoo/Desktop/rythmgame/Coupe ! (Feat. lobonabeat!).mp3", difficulty="Normal")
    game.run()
