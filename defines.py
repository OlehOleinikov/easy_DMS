import winsound


def melody_run():
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


rich_fonts = ['slant', 'banner3-D', 'ogre', 'xsbook', 'utopia', 'univers', 'ucf_fan_',
              'type_set', 'ttyb', 'twin_cob', 'trashman', 'trek', 'tombstone', 'taxi____',
              'stop', 'starwars', 'standard', 'speed', 'space_op', 'smslant', 'shadow',
              'script', 'rozzo', 'rounded', 'roman']
