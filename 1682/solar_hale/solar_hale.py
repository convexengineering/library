from gpkit import Variable, Model, units
import numpy as np
import matplotlib.pyplot as plt


class SolarHALE(Model):
    """High altitude long endurance solar UAV"""
    def __init__(self, **kwargs):
        """Setup method should return objective, list of constraints"""
        constraints = []

        # Steady level flight relations
        CD = Variable('C_D', '-', 'Drag coefficient')
        CL = Variable('C_L', '-', 'Lift coefficient')
        P_shaft = Variable('P_{shaft}', 'W', 'Shaft power')
        S = Variable('S', 'm^2', 'Wing reference area')
        V = Variable('V', 'm/s', 'Cruise velocity')
        W = Variable('W', 'lbf', 'Aircraft weight')

        eta_prop = Variable(r'\eta_{prop}', 0.7, '-', 'Propulsive efficiency')
        rho = Variable(r'\rho', 'kg/m^3')

        constraints.extend([P_shaft >= V*W*CD/CL/eta_prop,   # eta*P = D*V
                            W == 0.5*rho*V**2*CL*S])

        # Aerodynamics model
        Cd0 = Variable('C_{d0}', 0.002, '-', "non-wing drag coefficient")
        cdp = Variable("c_{dp}", "-", "wing profile drag coeff")
        CLmax = Variable('C_{L-max}', 1.5, '-', 'maximum lift coefficient')
        e = Variable('e', 0.9, '-', "spanwise efficiency")
        AR = Variable('AR', 27, '-', "aspect ratio")
        b = Variable('b', 'ft', 'span')
        mu = Variable(r'\mu', 1.5e-5, 'N*s/m^2', "dynamic viscosity")
        Re = Variable("Re", '-', "Reynolds number")
        Re_ref = Variable("Re_{ref}", 3e5, "-", "Reference Re for cdp")
        Cf = Variable("C_f", "-", "wing skin friction coefficient")
        Kwing = Variable("K_{wing}", 1.3, "-", "wing form factor")
        constraints.extend([
            CD >= (Cd0 + cdp + CL**2/(np.pi*e*AR))*1.3,
            cdp >= ((0.006 + 0.005*CL**2 + 0.00012*CL**10)*(Re/Re_ref)**-0.3),
            b**2 == S*AR,
            CL <= CLmax,
            Re == rho*V/mu*(S/AR)**0.5,
            ])

        # Weight model
        W_batt = Variable('W_{batt}', 'lbf', 'Battery weight')
        W_airframe = Variable('W_{airframe}', 'lbf', 'Airframe weight')
        W_solar = Variable('W_{solar}', 'lbf', 'Solar panel weight')
        W_pay = Variable(r'W_{pay}', 4, 'lbf', 'Aircraft weight')

        E_batt = Variable('E_{batt}', 'J', 'Battery energy')
        rho_solar = Variable(r'\rho_{solar}', 1.2, 'kg/m^2',
                             'Solar cell area density')
        f_airframe = Variable('f_{airframe}', 0.20, '-',
                              'Airframe weight fraction')
        h_batt = Variable('h_{batt}', 250, 'W*hr/kg', 'Battery energy density')
        g = Variable('g', 9.81, 'm/s^2', 'Gravitational acceleration')

        constraints.extend([W_airframe >= W*f_airframe,
                            W_batt >= E_batt/h_batt*g,
                            W_solar >= rho_solar*g*S,
                            W >= W_pay + W_solar + W_airframe + W_batt])

        # Power model
        PS_irr = Variable('(P/S)_{irr}', 1000*0.5, 'W/m^2',
                          'Average daytime solar irradiance')
        P_oper = Variable('P_{oper}', 'W', 'Aircraft operating power')
        P_charge = Variable('P_{charge}', 'W', 'Battery charging power')
        P_acc = Variable('P_{acc}', 25, 'W', 'Accessory power draw')
        eta_solar = Variable(r'\eta_{solar}', 0.2, '-',
                             'Solar cell efficiency')
        eta_charge = Variable(r'\eta_{charge}', 0.95, '-',
                              'Battery charging efficiency')
        eta_discharge = Variable(r'\eta_{discharge}', 0.95, '-',
                                 'Battery discharging efficiency')
        t_day = Variable('t_{day}', 'hr', 'Daylight span')
        t_night = Variable('t_{night}', 16, 'hr', 'Night span')

        constraints.extend([PS_irr*eta_solar*S >= P_oper + P_charge,
                            P_oper >= P_shaft + P_acc,
                            P_charge >= E_batt/(t_day*eta_charge),
                            t_day + t_night <= 24*units.hr,
                            E_batt >= P_oper*t_night/eta_discharge])

        # Atmosphere model
        h = Variable("h", "ft", "Altitude")
        p_sl = Variable("p_{sl}", 101325, "Pa", "Pressure at sea level")
        T_sl = Variable("T_{sl}", 288.15, "K", "Temperature at sea level")
        L_atm = Variable("L_{atm}", 0.0065, "K/m", "Temperature lapse rate")
        T_atm = Variable("T_{atm}", "K", "air temperature")
        M_atm = Variable("M_{atm}", 0.0289644, "kg/mol",
                         "Molar mass of dry air")
        R_atm = Variable("R_{atm}", 8.31447, "J/mol/K", "air specific heating value")
        TH = (g*M_atm/R_atm/L_atm).value
        constraints.extend([
            h <= 20000*units.m,  # Model valid to top of troposphere
            T_sl >= T_atm + L_atm*h,     # Temp decreases w/ altitude
            # http://en.wikipedia.org/wiki/Density_of_air#Altitude
            rho <= p_sl*T_atm**(TH-1)*M_atm/R_atm/(T_sl**TH)])

        # station keeping requirement
        footprint = Variable("d_{footprint}", 100, 'km',
                             "station keeping footprint diameter")
        lu = Variable(r"\theta_{look-up}", 5, '-', "look up angle")
        R_earth = Variable("R_{earth}", 6371, "km", "Radius of earth")
        tan_lu = lu*np.pi/180. + (lu*np.pi/180.)**3/3.  # Taylor series expansion
        # approximate earth curvature penalty as distance^2/(2*Re)
        constraints.extend([
            h >= tan_lu*0.5*footprint + footprint**2/8./R_earth])

        #----------------------------------------------------
        # wind speed model
        
        V_wind = Variable('V_{wind}', 10, 'm/s', 'wind speed')
        #wd_cnst = Variable('wd_{cnst}', 0.001077, 'm/s/ft', 
        #                   'wind speed constant predicted by model')
        #                    #0.002 is worst case, 0.0015 is mean at 45d
        #wd_ln = Variable('wd_{ln}', 8.845, 'm/s',
        #                 'linear wind speed variable')
        #               #13.009 is worst case, 8.845 is mean at 45deg
        #h_max = Variable('h_{max}', 20866, 'ft', 'maximum height')

        constraints.extend([#V_wind >= wd_cnst*h + wd_ln,
                            V >= V_wind
                            ])
        objective = W

        Model.__init__(self,objective,constraints, **kwargs)

if __name__ == "__main__":
    M = SolarHALE()
    M.solve("mosek")

    #M.substitutions.update({'V_{wind}': ('sweep', np.linspace(5,40,100))})
    #sol = M.solve(solver='mosek', verbosity=0, skipsweepfailures=True)
    #
    #W = sol('W')
    #b = sol('b')
    #V_wind = sol('V_{wind}')

    #plt.close()
    #plt.plot(V_wind, b)
    #plt.ylabel('wing span [ft]')
    #plt.xlabel('wind speed [m/s]')
    #plt.grid()
    #plt.axis([5,40,0,200])
    #plt.savefig('bvsV_wind.png')
