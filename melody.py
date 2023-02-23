"""Oldschool beeps for app execution stages"""
import winsound


def melody_loop():
    """Beeps series by next() func"""
    notes = [[416, 150], [392, 150], [370, 150]]
    notes.reverse()
    for note in notes:
        freq = note[0]
        dur = note[1]
        winsound.Beep(freq, dur)
    winsound.Beep(37, 2000)
    yield None
    notes.reverse()
    for note in notes:
        freq = note[0]
        dur = note[1]
        winsound.Beep(freq, dur)
    winsound.Beep(1000, 100)
    yield None
