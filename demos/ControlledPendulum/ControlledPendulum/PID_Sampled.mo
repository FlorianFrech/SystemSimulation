within ControlledPendulum;

model PID_Sampled
   /*
   The model implements a discrete PID controller that samples a reference and a state value
   at discrete time points defined by dt.
   Controller behavior is governed by Kp, Ki, and Kd.
   The output control signal u_control is limited to uMin and uMax values.
   */
  
   // Parameters
   parameter Real Kp = 100 "Proportional gain";
   parameter Real Ki = 500 "Integral gain";
   parameter Real Kd = 30 "Derivative gain";

   // Timing
   parameter Real dt(unit="s") = 0.01;

   // Limits
   parameter Real uMin=-1 "Minimum Control Output";
   parameter Real uMax=1 "Maximum Control Output";

   // Derivative on measurement flag
   parameter Boolean derivativeOnMeasurement = true "Compute derivative on measurement instead of error";


   // Inputs
   Modelica.Blocks.Interfaces.RealInput reference;
   Modelica.Blocks.Interfaces.RealInput measurement;

   // Output
   Modelica.Blocks.Interfaces.RealOutput u_control(start=0);
   Modelica.Blocks.Interfaces.RealOutput error;
   Modelica.Blocks.Interfaces.BooleanOutput saturated;

 protected
   // Continuous aliases for FMU compatibility
   Real ref_cont;
   Real meas_cont;

   // Internal discrete output
   discrete Real u(start=0, fixed=true) "Internal control signal";
   discrete Real e_k(start=0) "Current error";
   discrete Real e_km1(start=0, fixed=true) "Previous error";
   discrete Real meas_km1(start=0, fixed=true) "Previous measurement";
   discrete Real integral_sum(start=0, fixed=true) "Integral sum";
   discrete Real u_unsat(start=0) "Unsaturated control signal";
   
   // Algorithm coefficients
   discrete Real P_term;
   discrete Real I_term;
   discrete Real D_term;
  
   // Status flags
   discrete Boolean isSaturated(start=false);

 equation
   // Continuous aliases for FMU compatibility
   ref_cont   = reference;
   meas_cont  = measurement;
  
   // Continuous outputs
   u_control = u;
   error = e_k;
   saturated = isSaturated;

 algorithm
   when sample(0, dt) then
       // Current error
       e_k := ref_cont - meas_cont;

       // Update integral sum with anti-windup
       if not isSaturated then
           integral_sum := integral_sum + e_k * dt;
       end if;

       // Compute PID terms
       P_term := Kp * e_k;
       I_term := Ki * integral_sum;
       
       // Derivative on measurement (avoids derivative kick)
       if derivativeOnMeasurement then
           D_term := -Kd * (meas_cont - meas_km1) / dt;
       else
           D_term := Kd * (e_k - e_km1) / dt;
       end if;

       // Total control signal
       u_unsat := P_term + I_term + D_term;

       // Apply saturation limits
       u := min(uMax, max(uMin, u_unsat));

       // Check if saturated
       isSaturated := (u_unsat <= uMin) or (u_unsat >= uMax);

       // Update previous values
       e_km1 := e_k;
       meas_km1 := meas_cont;
   end when;

 initial algorithm
   // Initialize states
   e_km1 := ref_cont - meas_cont;
   meas_km1 := meas_cont;

end PID_Sampled;