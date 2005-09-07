#!/usr/bin/python
#-*- coding:"iso8859-15" -*-
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
  a_convertir = glob.glob('*.eje')
  #Elección del fir,sector y ejercicio
  config=ConfigParser()
  config.readfp(open('Madrid.fir','r'))
  # Puntos del FIR
  lista=config.items('PUNTOS')
  for (nombre,coord) in lista:
    print 'Leyendo punto ',nombre.upper(),
    (x,y)=coord.split(',')
    x=float(x)
    y=float(y)
    punto.append([nombre.upper(),(x,y)])
    print '...ok'
  # Rutas del FIR
  lista=config.items('RUTAS')
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
    hora = config.get('datos','hora_inicio')
    if hora=='':
      print 'No hay hora de inicio'
      ejercicio_bueno = False
    aviones = config.items('vuelos')
    config.set('datos','comentario',config.get('datos','comentario')+'('+str(len(aviones))+')')
    punto_entrada=[['KORUL','BHD'],['LOTEE','ALOTEE'],['ATLEN','AATLEN'],['PATEL','APATEL'],['ENDAY','BTZ'],['THUNE','BTZ'],['LURAN','TBO'],['LATEK','TOU'],['SOVAR','TBO'],['MARIO','GRAUS'],['KUMAN','GRAUS'],['PONEN','QUV'],['TOBAL','MLA'],['CLS','VLC'],['ASTRO','LEAL'],['ANZAN','BLN'],['LOGRO','ALOGRO'],['CRISA','ACRISA'],['MOLIN','HIJ'],['PARKA','AXACA'],['CCS','ELVAR'],['RAKOD','ARAKOD'],['ADORO','PRT'],['RALUS','VIS'],['NARBO','VIS'],['DEMOS','ORTIS'],['HIDRO','AHIDRO']]
    for (nombre,resto) in aviones:
      lista=resto.split(',')
      es_punto_entrada=True
      for i in range(len(lista[6:])):
        p=lista[i+6].upper()
        if len(p)==15:
          segundo=randint(0,59)
          lista[i+6]=p[:5]+'%02d' % (segundo)+p[7:]
        elif es_punto_entrada:
          es_punto_entrada = False
          if p == 'BARDI':
            if lista[i+6+1].upper() == 'NVS':
              lista.insert(i+6,'VIS')
            else:
              lista.insert(i+6,'ELVAR')
          for (entrada,anterior) in punto_entrada:
            if p==entrada:
              lista.insert(i+6,anterior)
      junto=lista[0]
      for d in lista[1:]:
        junto=junto+','+d
      config.set('vuelos',nombre,junto)
    config.write(open('./pasadas/'+ejercicio,'w'))
    # Cerrar ficheros y volver a empezar
    aux=config.sections()
    for a in aux:
      config.remove_section(a)
  return


tpv()
