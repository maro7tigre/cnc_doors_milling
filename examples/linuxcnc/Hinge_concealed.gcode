(--- L variables ---)
#1001={L1:7}
#1002={L2:30}
#1013={L13:23.5}
#1003={L3:111}
#1007={L7:77.5}
(--- custom variables ---)
#1180={x offset:0}
#1181={y offset:0}
#1182={z offset:0}
#1101={slow feed:1000}
#1102={fast feed:1500}
#1103={max mill:5}

(--- computed once at top ---)
#<r>  = [#1013 * 0.5]       ; arc radius = L13/2
#<yd> = 0                   ; accumulated depth from starting point

o102 if [#<_x_sign> EQ -1]
	#<g41> = 41
	#<g42> = 42
	#<g2>  = 2
	#<g3>  = 3
o102 else
	#<g41> = 42
	#<g42> = 41
	#<g2>  = 3
	#<g3>  = 2
o102 endif

(--- setup ---)
G91 G18

(--- move to the starting position ---)
G40 G1 X[#<_x_sign>*#1180] Y[#1181] Z[#1182] F[#1102]
G[#<g42>] G1 X[#<_x_sign>*#<r>] F[#1102]
G1 Y20 F[#1101]
(--- start ---)
o103 while [#<yd> LT #1001]
  #<s> = [#1001 - #<yd>]
  o104 if [#<s> GT #1103]
    #<s> = #1103
  o104 endif
  #<yd> = [#<yd> + #<s>]

  G1 Y[#<s>] F[#1101]
  G1 X[#<_x_sign>*[#1003-#1013]] F[#1102]
  G[#<g2>] X0 Z-[#1013] R[#<r>]
  G1 X-[#<_x_sign>*[#1003-#1013]]
  G[#<g2>] X0 Z[#1013] R[#<r>]
o103 endwhile

  #<yd> = 0
  G1 X[#<_x_sign>*[#1003-#1007]/2] F[#1102]	

o105 while [#<yd> LT #1002]
  #<s> = [#1002 - #<yd>]
  o106 if [#<s> GT #1103]
    #<s> = #1103
  o106 endif
  #<yd> = [#<yd> + #<s>]

  G1 Y[#<s>] F[#1101]
  G1 X[#<_x_sign>*[#1007-#1013]] F[#1102]
  G[#<g2>] X0 Z-[#1013] R[#<r>]     
  G1 X-[#<_x_sign>*[#1007-#1013]]     
  G[#<g2>] X0 Z[#1013] R[#<r>]  
o105 endwhile

G1 Y-[#1002+#1001+20] F[#1101] 
G40 G1 X-[#<_x_sign>*#<r>] F[#1102]
G90 G17