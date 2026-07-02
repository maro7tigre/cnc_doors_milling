(--- start up ---)
G90 G55 G17 G40
#<_x_sign> = -1

G52 X0 Y0 Z{$door_depth}


(--- repeat ---)
#<order> = 1
o10 repeat [12]
	o11 if [{$hinge1_active} EQ #<order>]
		o100 call [{$hinge1_x_position}] [-{$hinge_z_position}]
	o11 endif
	o12 if [{$hinge2_active} EQ #<order>]
		o100 call [{$hinge2_x_position}] [-{$hinge_z_position}]
	o12 endif
	o13 if [{$hinge3_active} EQ #<order>]
		o100 call [{$hinge3_x_position}] [-{$hinge_z_position}]
	o13 endif
	o14 if [{$hinge4_active} EQ #<order>]
		o100 call [{$hinge4_x_position}] [-{$hinge_z_position}]
	o14 endif
	o15 if [{$hinge5_active} EQ #<order>]
		o100 call [{$hinge5_x_position}] [-{$hinge_z_position}]
	o15 endif
	o16 if [{$hinge6_active} EQ #<order>]
		o100 call [{$hinge6_x_position}] [-{$hinge_z_position}]
	o16 endif
	o17 if [{$hinge7_active} EQ #<order>]
		o100 call [{$hinge7_x_position}] [-{$hinge_z_position}]
	o17 endif
	o18 if [{$hinge8_active} EQ #<order>]
		o100 call [{$hinge8_x_position}] [-{$hinge_z_position}]
	o18 endif
	o19 if [{$hinge9_active} EQ #<order>]
		o100 call [{$hinge9_x_position}] [-{$hinge_z_position}]
	o19 endif
	o20 if [{$hinge10_active} EQ #<order>]
		o100 call [{$hinge10_x_position}] [-{$hinge_z_position}]
	o20 endif
	o21 if [{$lock_active} EQ #<order>]
		o200 call [{$door_height}-{$lock_x_position}] [{$lock_z_position}]
	o21 endif
	o22 if [{$barrel_active} EQ #<order>]
		o300 call [{$door_height}-{$barrel_x_position}] [{$barrel_y_position}]
	o22 endif
#<order> = [#<order> + 1]
o10 endrepeat

(--- end of program ---)
G90 G17 G40
G53 G0 Z0
M5 $0
M5 $1
M5 $2
G53 G0 X0 Y0
M30



(--- SEUBNETS ---)
(--- HINGES SUBROUTINE ---)
o100 sub 
G90 G17 G40

o190 if [#<_selected_tool> NE 21]
 M5 $0
 M5 $2
o190 endif

 M6 T21
 G43 H21

o191 if [#<_y> GT -10]
  G53 G0 Z0
o191 endif
G0 Y-20
G0 X[#<_x_sign>*#1] Z[#2]
M3 $1 S1300
{$hinges_gcode}
o100 endsub

(--- LOCK SUBROUTINE ---)
o200 sub 
M5 $0
M5 $2
G90 G17 G40
M6 T22
G43 H22

G53 G0 Z0
G0 Y[{$door_width}+20]
G0 X[#<_x_sign>*#1] Z[#2]
M3 $1 S3000

{$lock_gcode}
o200 endsub

(--- BARREL SUBROUTINE ---)
o300 sub 
M5 $1
M5 $2
G90 G17 G40
M6 T1
G43 H1

G53 G0 Z0

G0 X[#<_x_sign>*#1] Y[#2]

G1 Z20
M3 $0 S12000

{$barrel_gcode}
o300 endsub