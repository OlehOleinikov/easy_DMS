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

color1 = '#FF00FF'
color2 = '#0040FF'
color3 = '#01FFFF'

intro_ascii =   f"[{color2}]_________________________________________________________\n" \
                f"[{color2}]_/_____//_____//_____//_____//_____//_____//_____//_____/\n"\
                f"\n"\
                f"\n"\
                f"[{color1}]__________                          ______________  __________\n"\
                f"[{color1}]___  ____/_____ ____________  __    ___  __ \__   |/  /_  ___/\n"\
                f"[{color2}]__  __/  _  __ `/_  ___/_  / / /    __  / / /_  /|_/ /_____ \ \n"\
                f"[{color2}]_  /___  / /_/ /_(__  )_  /_/ /     _  /_/ /_  /  / / ____/ / \n"\
                f"[{color3}]/_____/  \__,_/ /____/ _\__, /      /_____/ /_/  /_/  /____/\n"\
                f"[{color3}]                       /____/                                 \n"\
                f"\n"\
                f"\n"\
                f"[{color2}]_________________________________________________________\n"\
                f"[{color2}]_/_____//_____//_____//_____//_____//_____//_____//_____/\n"