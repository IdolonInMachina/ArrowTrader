import main
import os
import time

os.system(f"mode 150,{os.get_terminal_size().lines + 10}")

__version__ = "1.0.1"


def show_art():
    time.sleep(2)
    title_art()
    print(f"\tVersion: {__version__}\n")
    time.sleep(2)
    dedication_art()
    time.sleep(2)
    attribution_art()
    time.sleep(3)


def title_art():
    art = '''      >>                                               >===>>=====>                         >=>                   
     >>=>                                                   >=>                             >=>                   
    >> >=>     >> >==> >> >==>    >=>     >=>      >=>      >=>     >> >==>    >=> >=>      >=>   >==>    >> >==> 
   >=>  >=>     >=>     >=>     >=>  >=>   >=>  >  >=>      >=>      >=>     >=>   >=>   >=>>=> >>   >=>   >=>    
  >=====>>=>    >=>     >=>    >=>    >=>  >=> >>  >=>      >=>      >=>    >=>    >=>  >>  >=> >>===>>=>  >=>    
 >=>      >=>   >=>     >=>     >=>  >=>   >=>>  >=>=>      >=>      >=>     >=>   >=>  >>  >=> >>         >=>    
>=>        >=> >==>    >==>       >=>     >==>    >==>      >=>     >==>      >==>>>==>  >=>>=>  >====>   >==> 
'''
    print('\n\n')
    print(art)


def dedication_art():
    art = '''                                        
.--       .  . ..-.,-..-.  .-.          
|-.-..-.  |  |-|`-. / | |  |-..-. .-..-.
' `-''    '-'' '`-''--`-'  '-'`-`-' '`-|
                                    `-'
'''
    print('\n\n')
    print(art)


def attribution_art():
    art = '''.-.     -.-  .    . 
|< . .   | .-| .-.| 
'-''-|  -'-`-'-`-''-
   `-'              
'''
    print('\n\n')
    print(art)


if __name__ == '__main__':
    show_art()
    main.run()
