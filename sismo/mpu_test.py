# Prueba basica de la MPU6050 en el bus I2C por software (GPIO23 = SDA, GPIO24 = SCL).
# Requiere en /boot/firmware/config.txt:
#   dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=23,i2c_gpio_scl=24
import smbus, time
bus = smbus.SMBus(3)
ADDR = 0x68
bus.write_byte_data(ADDR, 0x6B, 0)  # sacar del modo sleep
def rd(reg):
    v = (bus.read_byte_data(ADDR, reg) << 8) | bus.read_byte_data(ADDR, reg + 1)
    return v - 65536 if v > 32767 else v
print("WHO_AM_I:", hex(bus.read_byte_data(ADDR, 0x75)))
while True:
    ax, ay, az = (rd(r) / 16384 for r in (0x3B, 0x3D, 0x3F))
    gx, gy, gz = (rd(r) / 131 for r in (0x43, 0x45, 0x47))
    t = rd(0x41) / 340 + 36.53
    print(f"a(g)=({ax:+.2f},{ay:+.2f},{az:+.2f}) gyro=({gx:+.1f},{gy:+.1f},{gz:+.1f}) T={t:.1f}C")
    time.sleep(0.2)
