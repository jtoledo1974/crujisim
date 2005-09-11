#!/usr/bin/python
#-*- coding:"iso8859-15" -*-

# (c) 2005 CrujiMaster (crujisim@yahoo.com)
#
# This file is part of CrujiSim.
#
# CrujiSim is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# CrujiSim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CrujiSim; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import warnings
warnings.filterwarnings('ignore','.*',DeprecationWarning)
from ConfigParser import *
from avion import *
import glob
from Tkinter import *
from random import *

def tpv(): 

  punto = []
  ejercicio = []
  rutas = []
  limites = []
  a_convertir = glob.glob('./pasadas_app_raw/83*.eje')
  #Elección del fir,sector y ejercicio
  config=ConfigParser()
  config.readfp(open('AppRadarBasico.fir','r'))
  # Puntos del FIR
  lista=config.items('puntos')
  for (nombre,coord) in lista:
    print 'Leyendo punto ',nombre.upper(),
    (x,y)=coord.split(',')
    x=float(x)
    y=float(y)
    punto.append([nombre.upper(),(x,y)])
    print '...ok'
  # Rutas del FIR
  lista=config.items('rutas')
  for (num,aux) in lista:
    print 'Leyendo ruta ',num,
    linea=aux.split(',')
    aux2=()
    for p in linea:
      for q in punto:
        if p==q[0]:
          aux2=aux2+q[1]
    rutas.append([aux2])
    print '...ok'
  aux=config.sections()
  for a in aux:
    config.remove_section(a)
 
  for ejercicio in a_convertir:
    ejercicio_bueno = True
    # Ahora se crean los planes de vuelo del ejercicio
    print 'Leyendo archivo ',ejercicio
    config.readfp(open(ejercicio,'r'))
    config.set('datos','fir','AppRadarBasico')
    hora = config.get('datos','hora_inicio')
    config.set('datos','sector','AppRadarBasico')
    if hora=='':
      print 'No hay hora de inicio'
      ejercicio_bueno = False
    aviones = config.items('vuelos')
    config.set('datos','comentario',config.get('datos','comentario')+'('+str(len(aviones))+')')
#     punto_entrada=[['KORUL','BHD'],['LOTEE','ALOTEE'],['ATLEN','AATLEN'],['PATEL','APATEL'],['ENDAY','BTZ'],['THUNE','BTZ'],['LURAN','TBO'],['LATEK','TOU'],['SOVAR','TBO'],['MARIO','GRAUS'],['KUMAN','GRAUS'],['PONEN','QUV'],['TOBAL','MLA'],['CLS','VLC'],['ASTRO','LEAL'],['ANZAN','BLN'],['LOGRO','ALOGRO'],['CRISA','ACRISA'],['MOLIN','HIJ'],['PARKA','AXACA'],['CCS','ELVAR'],['RAKOD','ARAKOD'],['ADORO','PRT'],['RALUS','VIS'],['NARBO','VIS'],['DEMOS','ORTIS'],['HIDRO','AHIDRO']]
    for (nombre,resto) in aviones:
      lista=resto.split(',')
      if lista[4] == '020':
        lista[4] = lista[5]
      es_punto_entrada=True
      for i in range(len(lista[6:])):
        p=lista[i+6].upper()
        if p == 'LEMD':
          if len(lista)>=i+8  and lista[i+8] == 'BRA':
            lista[i+6]='BRA'
            lista[i+8]='quitar'
          else:
            lista[i+6] = 'quitar'
        elif p == '2DME':
          lista[i+6] = '_2DME'
        elif p == 'PDT':
          if len(lista[i+7]) > 8:
            i=i+1
          for kk in range(i+7,len(lista)):
            lista.pop(-1)
          break
      junto=lista[0]
      for d in lista[1:]:
        if d != 'quitar':
          junto=junto+','+d
      config.set('vuelos',nombre,junto)
    aviones = config.items('vuelos')
    for (nombre,resto) in aviones:
      lista = resto.split(',')
      for i in range(len(lista[6:])):
        p=lista[i+6].upper()
        if len(p)==15 and lista[6]=='BRA':
          lista[i+6]=p[:8]+'020'+p[11:]
          break
      junto=lista[0]
      for d in lista[1:]:
        junto=junto+','+d
      config.set('vuelos',nombre,junto)
    config.write(open('./pasadas_app_tratadas/'+ejercicio[18:],'w'))
    # Cerrar ficheros y volver a empezar
    aux=config.sections()
    for a in aux:
      config.remove_section(a)
  return


tpv()
