from pivovar import update

from textwrap import dedent


def test_machine_id():
    hostnamectl = dedent("""\
           Static hostname: unipi-stretch
        Transient hostname: M103-sn116
                 Icon name: computer
                Machine ID: 021eba9b75b94f26942263c5cc92c2d6
                   Boot ID: 8953532f94914fe5987eb66702814dea
          Operating System: Raspbian GNU/Linux 9 (stretch)
                    Kernel: Linux 4.9.41-v7+
              Architecture: arm
      """)
    assert ('021eba9b75b94f26942263c5cc92c2d6'
            == update.get_machine_id(hostnamectl))
