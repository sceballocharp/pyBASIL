// PYNQ Microblaze driver for HearLight LED control system
// Ryan Greer, University of Strathclyde
// 9th December 2022
// Updated for new control system v2: June 2025

#include <gpio.h>
#include <spi.h>
#include <timer.h>
#include <pyprintf.h>
#include <stdint.h>

#define LTC2662_CMD_POWER_DOWN_N 0x40
#define LTC2662_CMD_SPAN 0x60
#define LTC2662_CMD_WRITE_N_UPDATE_N 0x30
#define LTC2662_CMD_WRITE_CODE_N 0x00
#define LTC2662_CMD_UPDATE_ALL 0x90
#define LTC2662_CMD_UPDATE_N 0x10
#define LTC2662_CMD_WRITE_ALL_UPDATE_ALL 0xA0

#include <xparameters.h>
#include <xsysmon.h>
#define SYSMON_DEVICE_ID XPAR_SYSMON_0_DEVICE_ID

static XSysMon SysMonInst;
XSysMon_Config *SysMonConfigPtr;
XSysMon *SysMonInstPtr = &SysMonInst;

spi dac;
gpio cs_a;
gpio cs_b;
gpio cs_c;
gpio cs_d;
gpio sr_data;
gpio sr_clk;
gpio sr_latch;
gpio sr_clr_n;

gpio trig_in_1;
gpio trig_in_2;

int16_t fault_code = 0;
uint32_t max_switch_counts = 0;
uint32_t max_device_counts = 0;
float dac_refs[8] = {3.125, 6.25, 12.5, 25, 50, 100, 200, 300};

/*
Function to transfer block through SPI.
*/
int8_t dac_write(gpio *cs_handle, uint8_t dac_command, uint8_t selected_dac, uint16_t dac_code){
    // length 3 which corresponds to shorter address of 24 bits
    char tx_array[3];
    char rx_array[3];

    tx_array[0] = dac_command + selected_dac;
    tx_array[1] = (dac_code >> 8) & 0xFF;
    tx_array[2] = dac_code & 0xFF;

    gpio_write(*cs_handle, 0);
    spi_transfer(dac, tx_array, rx_array, 3);
    gpio_write(*cs_handle, 1);
    
    return rx_array[0]; // fault code
}

/*
sets softspan range of all DACs based on 'current_ref'
            'current_ref' sets softspan range (maximum current)
                0 : 3.125 mA
                1 : 6.25 mA
                2 : 12.5 mA
                3 : 25 mA
                4 : 50 mA
                5 : 100 mA
                6 : 200 mA
                7 : 300 mA
*/
int8_t dac_config(uint8_t channel, uint16_t current_ref){
    int8_t fault_reg = 0;
    
    uint8_t selected_dac = channel % 5;
    
    uint8_t user_command = 0;
    
    if(current_ref == 0){
        user_command = 1;        
    }
    else if(current_ref == 1){
        user_command = 2;
    }
    else if(current_ref == 2){
        user_command = 3;
    }
    else if(current_ref == 3){
        user_command = 4;
    }
    else if(current_ref == 4){
        user_command = 5;
    }
    else if(current_ref == 5){
        user_command = 6;
    }
    else if(current_ref == 6){
        user_command = 7;
    }
    else if(current_ref == 7){
        user_command = 15;
    }
    else if(current_ref == 8){
        user_command = 8;
    }
    
    if((channel >= 0) && (channel < 5)){
        fault_reg |= dac_write(&cs_a, LTC2662_CMD_SPAN, selected_dac, user_command);
    }
    else if((channel >= 5) && (channel < 10)){
        fault_reg |= dac_write(&cs_b, LTC2662_CMD_SPAN, selected_dac, user_command);
    }
    else if((channel >= 10) && (channel < 15)){
        fault_reg |= dac_write(&cs_c, LTC2662_CMD_SPAN, selected_dac, user_command);
    }
    else{
        fault_reg |= dac_write(&cs_d, LTC2662_CMD_SPAN, selected_dac, user_command);
    }

    return fault_reg;
}

/*
Switches on/off DAC channel indicated by 'channel' argument and considers both DACs
            'channel' => 0->19
            'on_off' => '1' is on and '0' is off
            'current_code' => current value in DAC counts
*/
int8_t dac_channel_control(uint8_t channel, uint8_t on_off, uint16_t current_code){
    int8_t fault_reg = 0;
    
    uint8_t selected_dac = channel % 5;
    
    if(on_off){
        if((channel >= 0) && (channel < 5)){
            fault_reg |= dac_write(&cs_a, LTC2662_CMD_WRITE_N_UPDATE_N, selected_dac, current_code);
        }
        else if((channel >= 5) && (channel < 10)){
            fault_reg |= dac_write(&cs_b, LTC2662_CMD_WRITE_N_UPDATE_N, selected_dac, current_code);
        }
        else if((channel >= 10) && (channel < 15)){
            fault_reg |= dac_write(&cs_c, LTC2662_CMD_WRITE_N_UPDATE_N, selected_dac, current_code);
        }
        else{
            fault_reg |= dac_write(&cs_d, LTC2662_CMD_WRITE_N_UPDATE_N, selected_dac, current_code);
        }
    }
    else{
        if((channel >= 0) && (channel < 5)){
            fault_reg |= dac_write(&cs_a, LTC2662_CMD_POWER_DOWN_N, selected_dac, current_code);
        }
        else if((channel >= 5) && (channel < 10)){
            fault_reg |= dac_write(&cs_b, LTC2662_CMD_POWER_DOWN_N, selected_dac, current_code);            
        }
        else if((channel >= 10) && (channel < 15)){
            fault_reg |= dac_write(&cs_c, LTC2662_CMD_POWER_DOWN_N, selected_dac, current_code);
        }
        else{
            fault_reg |= dac_write(&cs_d, LTC2662_CMD_POWER_DOWN_N, selected_dac, current_code);
        }
    }
    
    return fault_reg;
}

/*
Opens/closes switches in the switch arrays based on 'sw' argument
            'open_close' = '1' is switch closed and '0' is switch open
*/
void switch_control(gpio *sw, uint8_t open_close){
    if(open_close){
        gpio_write(*sw, 0);     
    }
    else{
        gpio_write(*sw, 1);             
    }
}

/*
Opens/closes switches in the switch arrays based on 'sw' argument using shift register
            'open_close' = '1' is switch closed and '0' is switch open
*/
void switch_control_sr(uint8_t sw, uint8_t open_close){
    
}

/*
Returns 16-bit fault code which indicates which channels have had current corrected due to exceeding limit on system.
10 least significant bits with '1' indicating fault, '0' with no fault, LSB is channel 1 (P1).
*/
int16_t leds_read_fault(){
    return fault_code;
}

/*
Configures DACs and GPIOs for switches, must be called before 'leds_start'
*/
void leds_configure(uint8_t dac_ref, int max_switch_current, int max_device_current){
    // RPC handle to control DACs through SPI
    dac = spi_open(13, 12, 11, 6);
    delay_ms(100); // small delay required or first SPI transfers not recognised
    
    // chip select for DACs A to D B - initialise to 'high' (slave disabled)
    cs_a = gpio_open(9);
    gpio_set_direction(cs_a, GPIO_OUT);
    gpio_write(cs_a, 1);
    
    cs_b = gpio_open(7);
    gpio_set_direction(cs_b, GPIO_OUT);
    gpio_write(cs_b, 1);
    
    cs_c = gpio_open(10);
    gpio_set_direction(cs_c, GPIO_OUT);
    gpio_write(cs_c, 1);
    
    cs_d = gpio_open(8);
    gpio_set_direction(cs_d, GPIO_OUT);
    gpio_write(cs_d, 1);
    
    // switch array control through shift register
    sr_data = gpio_open(2);
    gpio_set_direction(sr_data, GPIO_OUT);
    gpio_write(sr_data, 0);
    
    sr_clk = gpio_open(4);
    gpio_set_direction(sr_clk, GPIO_OUT);
    gpio_write(sr_clk, 0);
    
    sr_latch = gpio_open(3);
    gpio_set_direction(sr_latch, GPIO_OUT);
    gpio_write(sr_latch, 0);    
    
    sr_clr_n = gpio_open(5);
    gpio_set_direction(sr_clr_n, GPIO_OUT);
    gpio_write(sr_clr_n, 1);
    
    // trigger inputs - pins A4 (17) and A5 (18)
    //trig_in_1 = gpio_open(0);
    trig_in_1 = gpio_open(18);
    gpio_set_direction(trig_in_1, GPIO_IN);
    
    trig_in_2 = gpio_open(17);
    gpio_set_direction(trig_in_2, GPIO_IN);    
    
    // set softspan range for all DACs
    for(uint8_t i = 0; i < 20; i++){
        dac_config(i, dac_ref);
    }
    
}

/*
Start LED patterns generating based on alloacted array in DDR memory. Only works for 10x10 currently.
*/
void leds_start(void* led_counts_buffer, void* trig, void* stop){
        
    // NEED TO HAVE 2 INPUTS - ONE FOR EACH CONNECTED DEVICE
    uint16_t (*led_counts)[20] = (uint16_t (*)[20])led_counts_buffer;
        
    uint16_t *trig_ptr = (uint16_t *) trig;
    *trig_ptr = 0;
    
    uint16_t *stop_ptr = (uint16_t *) stop;
        
    gpio_write(sr_clr_n, 0);
    gpio_write(sr_clr_n, 1);
    
    // set softspan for N track chips to switch to high Z
    dac_write(&cs_c, LTC2662_CMD_SPAN, 0, 0);
    dac_write(&cs_c, LTC2662_CMD_SPAN, 1, 0);
    dac_write(&cs_c, LTC2662_CMD_SPAN, 2, 0);
    dac_write(&cs_c, LTC2662_CMD_SPAN, 3, 0);
    dac_write(&cs_c, LTC2662_CMD_SPAN, 4, 0);
    dac_write(&cs_d, LTC2662_CMD_SPAN, 0, 0);
    dac_write(&cs_d, LTC2662_CMD_SPAN, 1, 0);
    dac_write(&cs_d, LTC2662_CMD_SPAN, 2, 0);
    dac_write(&cs_d, LTC2662_CMD_SPAN, 3, 0);
    dac_write(&cs_d, LTC2662_CMD_SPAN, 4, 0);

    dac_write(&cs_c, LTC2662_CMD_UPDATE_ALL, 0, 0);
    dac_write(&cs_d, LTC2662_CMD_UPDATE_ALL, 0, 0);
    
    for(uint8_t i = 0; i < 20; i++){
        gpio_write(sr_data, 1); // open switch
        gpio_write(sr_clk, 0);
        gpio_write(sr_latch, 0);
        gpio_write(sr_clk, 1);
        gpio_write(sr_latch, 1);
        gpio_write(sr_clk, 0);
        gpio_write(sr_latch, 0);
    }
    
    // For UOA
    // loop forever
    while(1){
        
        if(*stop_ptr == 1){
            // set channel currents to zero
            for(uint8_t i = 0; i < 20; i++){
                dac_channel_control(i, 0, 0);
            }
            break;
        }
        
        *trig_ptr = gpio_read(trig_in_1);
        
        
        // switch on single row for each matrix
        // for some reason I don't understand one switch must always be closed otherwise they all close (need to investigate with scope) - doesn't affect this implementation
        for(uint8_t i = 0; i < 10; i++){
            gpio_write(sr_data, 1); // open switch
            gpio_write(sr_clk, 0);
            gpio_write(sr_latch, 0);
            gpio_write(sr_clk, 1);
            gpio_write(sr_latch, 1);
            gpio_write(sr_clk, 0);
            gpio_write(sr_latch, 0);
        }
        
        gpio_write(sr_data, 0); // close switch
        
        for(uint8_t sw = 0; sw < 10; sw++){
            
            // set channel currents to zero
            // dac_write(&cs_a, LTC2662_CMD_WRITE_ALL_UPDATE_ALL, 0, 0);
            // dac_write(&cs_b, LTC2662_CMD_WRITE_ALL_UPDATE_ALL, 0, 0);
            for(uint8_t i = 0; i < 20; i++){
                dac_channel_control(i, 0, 0);
            }
            
            // use sr to switch to GND
            // switch on single row for each matrix
            // for some reason I don't understand one switch must always be closed otherwise they all close (need to investigate with scope) - doesn't affect this implementation
            
            gpio_write(sr_clk, 0);
            gpio_write(sr_latch, 0);
            gpio_write(sr_clk, 1);
            gpio_write(sr_latch, 1);
            gpio_write(sr_data, 1); // open switch
            
            // set current DAC values
            dac_write(&cs_a, LTC2662_CMD_WRITE_CODE_N, 0, led_counts[sw][0]);
            dac_write(&cs_a, LTC2662_CMD_WRITE_CODE_N, 1, led_counts[sw][1]);
            dac_write(&cs_a, LTC2662_CMD_WRITE_CODE_N, 2, led_counts[sw][2]);
            dac_write(&cs_a, LTC2662_CMD_WRITE_CODE_N, 3, led_counts[sw][3]);
            dac_write(&cs_a, LTC2662_CMD_WRITE_CODE_N, 4, led_counts[sw][4]);
            dac_write(&cs_b, LTC2662_CMD_WRITE_CODE_N, 0, led_counts[sw][5]);
            dac_write(&cs_b, LTC2662_CMD_WRITE_CODE_N, 1, led_counts[sw][6]);
            dac_write(&cs_b, LTC2662_CMD_WRITE_CODE_N, 2, led_counts[sw][7]);
            dac_write(&cs_b, LTC2662_CMD_WRITE_CODE_N, 3, led_counts[sw][8]);
            dac_write(&cs_b, LTC2662_CMD_WRITE_CODE_N, 4, led_counts[sw][9]);
            dac_write(&cs_a, LTC2662_CMD_UPDATE_ALL, 0, 0);
            dac_write(&cs_b, LTC2662_CMD_UPDATE_ALL, 0, 0);
            
            // if any values are set to zero, switch supply off
            for(uint8_t i=0; i<10; i++){
                if(led_counts[sw][i] == 0){
                    dac_channel_control(i, 0, 0);
                }
            }
            
            
            // new - switch off dac channel when value is zero
            // for(uint8_t i=0; i<10; i++){
            //     if(led_counts[sw][i] == 0){
            //         dac_channel_control(i, 0, 0);
            //     }
            //     else{
            //         dac_channel_control(i, 1, led_counts[sw][i]);
            //     }
            // }
            
            delay_us(780);
        }
        
        // set channel currents to zero
        // dac_write(&cs_a, LTC2662_CMD_WRITE_ALL_UPDATE_ALL, 0, 0);
        // dac_write(&cs_b, LTC2662_CMD_WRITE_ALL_UPDATE_ALL, 0, 0);
        for(uint8_t i = 0; i < 20; i++){
            dac_channel_control(i, 0, 0);
        }
        
    }
        
    return;
}

/*
Connects output corresponding to 'channel' via mux to ADC
*/
#define LTC2662_CMD_MUX 0xb0
void monitor_mux(uint8_t channel){
    int8_t fault_reg = 0;
    uint8_t selected_dac = channel % 5;
    uint16_t mux_code = selected_dac + 24;
    
    fault_reg |= dac_write(&cs_a, LTC2662_CMD_MUX, 0, mux_code);
    fault_reg |= dac_write(&cs_b, LTC2662_CMD_MUX, 0, mux_code);
    fault_reg |= dac_write(&cs_c, LTC2662_CMD_MUX, 0, mux_code);
    fault_reg |= dac_write(&cs_d, LTC2662_CMD_MUX, 0, mux_code);
}

void read_adc(unsigned short *adc_data){
    
    u32 xStatus;
    
    // SysMon Initialize
    SysMonConfigPtr = XSysMon_LookupConfig(SYSMON_DEVICE_ID);
    if(SysMonConfigPtr == NULL)
        xil_printf("SysMon LookupConfig failed.\n\r");
    xStatus = XSysMon_CfgInitialize(SysMonInstPtr, SysMonConfigPtr,
                                    SysMonConfigPtr->BaseAddress);
    if(XST_SUCCESS != xStatus)
        xil_printf("SysMon CfgInitialize failed\r\n");
    // Clear the old status
    XSysMon_GetStatus(SysMonInstPtr);
    
    
    // wait
    // delay_ms(2000);
    
    // Wait for the conversion complete
    while ((XSysMon_GetStatus(SysMonInstPtr) & 
            XSM_SR_EOS_MASK) != XSM_SR_EOS_MASK);
    
    
    // uint16_t adc_data;
    adc_data[0] = XSysMon_GetAdcData(SysMonInstPtr, XSM_CH_AUX_MIN+1);  // A0
    adc_data[1] = XSysMon_GetAdcData(SysMonInstPtr, XSM_CH_AUX_MIN+9);  // A1
    adc_data[2] = XSysMon_GetAdcData(SysMonInstPtr, XSM_CH_AUX_MIN+6);  // A2
    adc_data[3] = XSysMon_GetAdcData(SysMonInstPtr, XSM_CH_AUX_MIN+15); // A3
    
    // return adc_data;
}

/*
Continuous pattern driver - updated for trigger signal.
    'current_dac_counts' contains 16-bit values for each current channel (0-19)
    'switches' least-signifcant 20 bits indicates if switch is closed or open
*/
void leds_start_cont(void *current_dac_counts_buffer, void *switches, void* trig_in, void* trig_out, void* stop, void* fault_reg_a_buffer, void* fault_reg_b_buffer, void* voltages_buffer){
    
    uint16_t *current_dac_counts = (uint16_t *) current_dac_counts_buffer;
    
    uint32_t *switches_ptr = (uint32_t *) switches;
    
    uint16_t *trig_in_ptr = (uint16_t *) trig_in;
    
    uint16_t *trig_out_ptr = (uint16_t *) trig_out;
    *trig_out_ptr = 0;
    
    uint16_t *stop_ptr = (uint16_t *) stop;
    
    int8_t fault_reg = 0;
    uint8_t *fault_reg_a = (uint8_t *) fault_reg_a_buffer;
    uint8_t *fault_reg_b = (uint8_t *) fault_reg_b_buffer;
    
    uint16_t *voltages = (uint16_t *) voltages_buffer;
    
    // set channel currents to zero
    for(uint8_t i = 0; i < 20; i++){
        dac_channel_control(i, 0, 0);
    }
    
    while(1){
        
        // wait until input trigger activated to control LEDs
        while(*trig_in_ptr == 0){
            *trig_out_ptr = gpio_read(trig_in_1);
            if(*stop_ptr == 1){
                break;
            }
        }
        if(*stop_ptr == 1){
            break;
        }
        
        // set channel currents to zero
        for(uint8_t i = 0; i < 20; i++){
            dac_channel_control(i, 0, 0);
        }

        // this loop opens all the switches except the ones that should be closed
        for(uint8_t sw_loop = 0; sw_loop < 20; sw_loop++){
            // if((sw_loop % 20) == sw){
            if((*switches_ptr & (0x0001<<sw_loop))){
                gpio_write(sr_data, 0); // close switch
            }
            else{
                gpio_write(sr_data, 1); // open switch
            }
            gpio_write(sr_clk, 0);
            gpio_write(sr_latch, 0);
            gpio_write(sr_clk, 1);
            gpio_write(sr_latch, 1);
            gpio_write(sr_clk, 0);
            gpio_write(sr_latch, 0);
        }

        // switch current channels to relevant values
        *fault_reg_a = 0;
        *fault_reg_b = 0;
        
        uint16_t adc_data[4];
        
        for(uint8_t i = 0; i < 20; i++){
            if(current_dac_counts[i] == 0){
                fault_reg = dac_channel_control(i, 0, 0);
            }
            else{
                fault_reg = dac_channel_control(i, 1, current_dac_counts[i]);
            }
            if(i < 5){
                //*fault_reg_a |= fault_reg;
                *fault_reg_a |= fault_reg;
            }
            else if(i < 10){
                *fault_reg_b |= fault_reg;
            }
            
            // set multiplexer and monitor voltage here - output to another function interface
            monitor_mux(i);
            read_adc(adc_data);
            if(i < 5){
                voltages[i] = adc_data[2];
            }
            else if(i < 10){
                voltages[i] = adc_data[0];
            }
            else if(i < 15){
                voltages[i] = adc_data[3];
            }
            else{
                voltages[i] = adc_data[1];
            }
        }
    }
    
    for(uint8_t i = 0; i < 20; i++){
        dac_channel_control(i, 0, 0);
    }
}


/*
Continuous pattern driver - similar to above but for health scan only
*/
void leds_start_cont_2(unsigned short *current_dac_counts, unsigned long switches){
            
    // set channel currents to zero
    for(uint8_t i = 0; i < 20; i++){
        dac_channel_control(i, 0, 0);
    }
            
    // set channel currents to zero
    for(uint8_t i = 0; i < 20; i++){
        dac_channel_control(i, 0, 0);
    }

    // this loop opens all the switches except the ones that should be closed
    for(uint8_t sw_loop = 0; sw_loop < 20; sw_loop++){
        // if((sw_loop % 20) == sw){
        if((switches & (0x0001<<sw_loop))){
            gpio_write(sr_data, 0); // close switch
        }
        else{
            gpio_write(sr_data, 1); // open switch
        }
        gpio_write(sr_clk, 0);
        gpio_write(sr_latch, 0);
        gpio_write(sr_clk, 1);
        gpio_write(sr_latch, 1);
        gpio_write(sr_clk, 0);
        gpio_write(sr_latch, 0);
    }

    // switch current channels to relevant values    
    for(uint8_t i = 0; i < 20; i++){
        if(current_dac_counts[i] == 0){
            dac_channel_control(i, 0, 0);
        }
        else{
            dac_channel_control(i, 1, current_dac_counts[i]);
        }
    }
}

void leds_off(){
    // set channel currents to zero
    for(uint8_t i = 0; i < 20; i++){
        dac_channel_control(i, 0, 0);
    }
}
