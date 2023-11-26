# AUTHOR [START]: Gayathri Girish Nair (23340334)
import time
from nanobot import Bot
import multiprocessing as mp
from rendezvous_server import Server

def start_process(type, name, port, marker=None, sensor_value=None):
    if type == 'server':
        process = mp.Process(target=Server, args=('127.0.0.1', port), name=name)
    elif type == 'bot':
        if marker is None or sensor_value is None:
            print('Please provide all arguments.')
        process = mp.Process(target=Bot, args=('127.0.0.1', port, marker, name, sensor_value), name=name)
    print(f'[{name}] UP!')
    process.start()
    return process

def stop_process(process, name):
    print(f'[{name}] DOWN!')
    process.kill()

def diagnosis_healthy_no_unreliability():
    ''' This function emulates the scenario wherein
        the bots diagnose the cell to be healthy
        without there having been any unreliability. 
    '''
    rv_server = start_process(type='server', name='RVServer', port=33000)
    bot_a = start_process(type='bot', name='botA', port=33001, marker='tumour', sensor_value=1)
    bot_b = start_process(type='bot', name='botB', port=33002, marker='acidity', sensor_value=1)
    bot_c = start_process(type='bot', name='botC', port=33003, marker='growth', sensor_value=0)
    bot_d = start_process(type='bot', name='botD', port=33004, marker='survivin', sensor_value=1)
    bot_e = start_process(type='bot', name='botE', port=33005, marker='ecmr', sensor_value=0)
    time.sleep(5)
    rv_server.kill()
    bot_a.kill()
    bot_b.kill()
    bot_c.kill()
    bot_d.kill()
    bot_e.kill()

def diagnosis_healthy_npbots_unreliable():
    ''' This function emulates the scenario wherein
        the bots diagnose the cell to be healthy
        but some of the non-primary bots are unreliable.
    '''
    rv_server = start_process(type='server', name='RVServer', port=33000)
    bot_a = start_process(type='bot', name='botA', port=33001, marker='tumour', sensor_value=1)
    bot_b = start_process(type='bot', name='botB', port=33002, marker='acidity', sensor_value=0)
    bot_c = start_process(type='bot', name='botC', port=33003, marker='growth', sensor_value=0)
    bot_e = start_process(type='bot', name='botE', port=33005, marker='ecmr', sensor_value=0)
    time.sleep(5)
    bot_d = start_process(type='bot', name='botD', port=33004, marker='survivin', sensor_value=0)
    stop_process(bot_b, 'botB')
    time.sleep(5)
    bot_b = start_process(type='bot', name='botB', port=33002, marker='acidity', sensor_value=0)
    time.sleep(35)
    rv_server.kill()
    bot_a.kill()
    bot_b.kill()
    bot_c.kill()
    bot_d.kill()
    bot_e.kill()

def diagnosis_healthy_server_unreliable():
    ''' This function emulates the scenario wherein
        the bots diagnose the cell to be healthy
        but the rendezvous server is unreliable.
    '''
    rv_server = start_process(type='server', name='RVServer', port=33000)
    bot_a = start_process(type='bot', name='botA', port=33001, marker='tumour', sensor_value=1)
    bot_b = start_process(type='bot', name='botB', port=33002, marker='acidity', sensor_value=0)
    bot_c = start_process(type='bot', name='botC', port=33003, marker='growth', sensor_value=1)
    stop_process(rv_server, 'RENDEZVOUS SERVER')
    bot_d = start_process(type='bot', name='botD', port=33004, marker='survivin', sensor_value=1)
    bot_e = start_process(type='bot', name='botE', port=33005, marker='ecmr', sensor_value=1)
    time.sleep(5)
    rv_server = start_process(type='server', name='RVServer', port=33000)
    time.sleep(30)
    rv_server.kill()
    bot_a.kill()
    bot_b.kill()
    bot_c.kill()
    bot_d.kill()
    bot_e.kill()

def diagnosis_cancer_pbot_unreliable():
    ''' This function emulates the scenario wherein
        the bots diagnose the cell to be cancerous
        but the primary bot is unreliable.
    '''
    rv_server = start_process(type='server', name='RVServer', port=33000)
    bot_a = start_process(type='bot', name='botA', port=33001, marker='tumour', sensor_value=1)
    bot_b = start_process(type='bot', name='botB', port=33002, marker='acidity', sensor_value=1)
    bot_c = start_process(type='bot', name='botC', port=33003, marker='growth', sensor_value=1)
    stop_process(bot_a, 'botA')
    bot_d = start_process(type='bot', name='botD', port=33004, marker='survivin', sensor_value=1)
    bot_e = start_process(type='bot', name='botE', port=33005, marker='ecmr', sensor_value=1)
    time.sleep(1)
    bot_a = start_process(type='bot', name='botA', port=33001, marker='tumour', sensor_value=1)
    time.sleep(40)
    rv_server.kill()
    bot_a.kill()
    bot_b.kill()
    bot_c.kill()
    bot_d.kill()
    bot_e.kill()

def diagnosis_cancer_no_unreliability():
    ''' This function emulates the scenario wherein
        the bots diagnose the cell to be cancerous
        without there having been any unreliability.
    '''
    rv_server = start_process(type='server', name='RVServer', port=33000)
    bot_a = start_process(type='bot', name='botA', port=33001, marker='tumour', sensor_value=1)
    bot_b = start_process(type='bot', name='botB', port=33002, marker='acidity', sensor_value=1)
    bot_c = start_process(type='bot', name='botC', port=33003, marker='growth', sensor_value=1)
    bot_d = start_process(type='bot', name='botD', port=33004, marker='survivin', sensor_value=1)
    bot_e = start_process(type='bot', name='botE', port=33005, marker='ecmr', sensor_value=1)
    time.sleep(5)
    rv_server.kill()
    bot_a.kill()
    bot_b.kill()
    bot_c.kill()
    bot_d.kill()
    bot_e.kill()

def no_cancer_suspicion():
    ''' This function emulates the scenario wherein
        the primary bot detects nothing and the team
        does not need to diagnose as there is no
        suspisicion of cancer. All bots diffuse as they
        are no longer needed in the body.
    '''
    rv_server = start_process(type='server', name='RVServer', port=33000)
    bot_b = start_process(type='bot', name='botB', port=33002, marker='acidity', sensor_value=1)
    bot_c = start_process(type='bot', name='botC', port=33003, marker='growth', sensor_value=1)
    bot_d = start_process(type='bot', name='botD', port=33004, marker='survivin', sensor_value=1)
    bot_e = start_process(type='bot', name='botE', port=33005, marker='ecmr', sensor_value=1)
    bot_a = start_process(type='bot', name='botA', port=33001, marker='tumour', sensor_value=0)
    time.sleep(65)
    rv_server.kill()
    bot_a.kill()
    bot_b.kill()
    bot_c.kill()
    bot_d.kill()
    bot_e.kill()

if __name__ == '__main__':
    print('\nSCENARIO 1: Diagnosis "healthy" with no unreliability.')
    diagnosis_healthy_no_unreliability()
    print('SCENARIO 1 COMPLETE :)')

    print('\nSCENARIO 2: Diagnosis "healthy" with non-primary bots being unreliable.')
    diagnosis_healthy_npbots_unreliable()
    print('SCENARIO 2 COMPLETE :)')

    print('\nSCENARIO 3: Diagnosis "healthy" with rendezvous server being unreliable.')
    diagnosis_healthy_server_unreliable()
    print('SCENARIO 3 COMPLETE :)')

    print('\nSCENARIO 4: Diagnosis "cancer" with primary bot being unreliable.')
    diagnosis_cancer_pbot_unreliable()
    print('SCENARIO 4 COMPLETE :)')
    
    print('\nSCENARIO 5: Diagnosis "cancer" with no unreliability.')
    diagnosis_cancer_no_unreliability()
    print('SCENARIO 5 COMPLETE :)')

    print('\nSCENARIO 6: No cancer suspicion so no need for diagnosis.')
    no_cancer_suspicion()
    print('SCENARIO 6 COMPLETE :)')
# AUTHOR [END]: Gayathri Girish Nair (23340334)