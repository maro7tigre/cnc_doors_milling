;lock's gcode will be here
(--- L variables ---)
#1001={L1:3}
#1002={L2:80}
#1013={L13:22}
#1003={L3:235}
#1004={L4:80}
#1007={L7:160}
#1012={L12:18}
(--- custom variables ---)
#1180={x offset:0}
#1181={y offset:0}
#1182={z offset:0}
#1101={slow feed:1000}
#1102={fast feed:3000}
#1103={max mill:6}


(--- computed once at top ---)
#<r13>  = [#1013 * 0.5]       ; arc radius = L13/2
#<r12>  = [#1012 * 0.5]
#<ctr>  = #5410 ; current tool raduis
o213 if [#<ctr> EQ 0]
  #<ctr> = 5
o213 endif

o202 if [#<_x_sign> EQ -1]
	#<g41> = 41
	#<g42> = 42
	#<g2>  = 2
	#<g3>  = 3
o202 else
	#<g41> = 42
	#<g42> = 41
	#<g2>  = 3
	#<g3>  = 2
o202 endif

(--- setup ---)
G91 G18

(--- move to the starting position ---)
G40 G1 X[#<_x_sign>*#1180] Y[#1181] Z[#1182] F[#1102]

(--- partial mill ---)
G1 X-[#<_x_sign>*[#1004-[[#1003-#1007]*0.5]-#<r12>]] F[#1102]
#<drill_c> = FIX[#1007 / #<ctr>]
o212 repeat[#<drill_c>]
	G1 Y-20 F[#1101]
	G1 Y-[#1001+#1002]
	G1 Y [#1001+#1002] F[#1102]
	G1 Y 20
	G1 X[#<_x_sign>*#<ctr>]
o212 endrepeat

o210 if [#<ctr> GE #1012]
 G1 X-[#<_x_sign>*#<ctr>*#<drill_c>] F[#1102]
o210 else
 G[#<g41>] G1 X-[#<_x_sign>*#<ctr>*#<drill_c>] Z#<r12> F[#1102]
o210 endif
G1 Y-20 F[#1101]
(--- start ---)
#<yd> = 0
#<stp> = 1
o203 while [#<yd> LT [#1001+#1002]]
  #<s> = [[#1001+#1002] - #<yd>]
  o204 if [#<s> GT #1103]
    #<s> = #1103
  o204 endif
   #<yd> = [#<yd> + #<s>]
   G1 Y-[#<s>] F[#1101]


  o205 if [#<ctr> GE #1012]
   G1 X[#<stp>*#<_x_sign>*[#1007-#1012]] F[#1102]

   o206 if [#<stp> EQ 1]
     #<stp> = -1
   o206 else
     #<stp> = 1
   o206 endif
  o205 else

   G[#<g3>] X0 Z-[#1012] R[#<r12>] F[#1102]
   G1 X[#<_x_sign>*[#1007-#1012]]
   G[#<g3>] X0 Z[#1012] R[#<r12>]
   G1 X-[#<_x_sign>*[#1007-#1012]] 
  o205 endif
o203 endwhile

G1 Y[#1001+#1002+10]
#<yd> = 0

 o207 if [#<stp> EQ -1]
  G0 X-[#<_x_sign>*[#1007-#1012]]
 o207 endif
 o211 if [#<ctr> LT #1012]
  G0 Z-#<r12>
 o211 endif
 G40 G1 X0
 G[#<g41>]  G0 X-[#<_x_sign>*[#<r12>+[[#1003-#1007]*0.5]-#<r13>]]	Z#<r13>
 G1 Y-10
o208 while [#<yd> LT #1001]
  #<s> = [#1001 - #<yd>]
  o209 if [#<s> GT #1103]
    #<s> = #1103
  o209 endif
  #<yd> = [#<yd> + #<s>]

  G1 Y-[#<s>] F[#1101]
  
  G[#<g3>] X0 Z-[#1013] R[#<r13>]     
  G1 X[#<_x_sign>*[#1003-#1013]]     
  G[#<g3>] X0 Z[#1013] R[#<r13>]
  G1 X-[#<_x_sign>*[#1003-#1013]] F[#1102]
o208 endwhile

G1 Y[#1001+20] F[#1101] 
G40 G1 X-[#<_x_sign>*#<r13>] F[#1102]
G90 G17