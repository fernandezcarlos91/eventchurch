# app.py - EventChurch - Hito 2

from flask import Flask, render_template, jsonify, abort

app = Flask(__name__)

# ==============================================================
# DATOS EN MEMORIA (simulando base de datos)
# ==============================================================

# Lista de eventos
EVENTOS = [
    {
        'id': 1,
        'nombre': 'Conferencia de Misiones 2026',
        'descripcion': 'Conferencia anual de misiones con invitados especiales',
        'fecha_inicio': '2026-08-15',
        'fecha_fin': '2026-08-17',
        'ubicacion': 'Templo Central',
        'estado': 'PLANEADO',
        'tipo_evento': 'MISIONES'
    },
    {
        'id': 2,
        'nombre': 'Celebración 15° Aniversario',
        'descripcion': 'Celebración del 15 aniversario de la iglesia',
        'fecha_inicio': '2026-05-20',
        'fecha_fin': '2026-05-20',
        'ubicacion': 'Templo Central',
        'estado': 'EN_PREPARACION',
        'tipo_evento': 'ANIVERSARIO'
    },
    {
        'id': 3,
        'nombre': 'Retiro de Familias',
        'descripcion': 'Retiro espiritual para familias',
        'fecha_inicio': '2026-07-10',
        'fecha_fin': '2026-07-12',
        'ubicacion': 'Centro de Retiros Paine',
        'estado': 'PLANEADO',
        'tipo_evento': 'FAMILIAS'
    }
]

# Lista de tareas
TAREAS = [
    {
        'id': 1,
        'titulo': 'Preparar lista de invitados',
        'descripcion': 'Hacer lista de invitados especiales',
        'evento_id': 1,
        'encargado': 'María Pérez',
        'fecha_limite': '2026-07-15',
        'completada': False
    },
    {
        'id': 2,
        'titulo': 'Coordinar música',
        'descripcion': 'Organizar el grupo de música',
        'evento_id': 1,
        'encargado': 'Pedro González',
        'fecha_limite': '2026-08-01',
        'completada': False
    },
    {
        'id': 3,
        'titulo': 'Organizar logística de alimentos',
        'descripcion': 'Coordinar comida para los asistentes',
        'evento_id': 1,
        'encargado': 'Juan López',
        'fecha_limite': '2026-08-10',
        'completada': False
    },
    {
        'id': 4,
        'titulo': 'Preparar programa del evento',
        'descripcion': 'Diseñar el programa del aniversario',
        'evento_id': 2,
        'encargado': 'Ana Martínez',
        'fecha_limite': '2026-05-10',
        'completada': True
    }
]

# ==============================================================
# FUNCIÓN AUXILIAR
# ==============================================================

def calcular_progreso(evento_id):
    """Calcula el porcentaje de avance de un evento"""
    tareas_evento = [t for t in TAREAS if t['evento_id'] == evento_id]
    if not tareas_evento:
        return 0
    completadas = sum(1 for t in tareas_evento if t['completada'])
    return round((completadas / len(tareas_evento)) * 100, 0)

def obtener_evento_con_progreso(evento):
    """Agrega el campo porcentaje_avance a un evento"""
    evento_con_progreso = dict(evento)
    evento_con_progreso['porcentaje_avance'] = calcular_progreso(evento['id'])
    return evento_con_progreso

# ==============================================================
# RUTAS HTML - Página de inicio
# ==============================================================

@app.route('/')
def inicio():
    """Página de inicio con estadísticas"""
    total_eventos = len(EVENTOS)
    total_tareas = len(TAREAS)
    tareas_completadas = sum(1 for t in TAREAS if t['completada'])
    
    # Calcular porcentaje global
    if total_tareas > 0:
        porcentaje_global = round((tareas_completadas / total_tareas) * 100, 0)
    else:
        porcentaje_global = 0
    
    return render_template('inicio.html',
        titulo='Inicio',
        total_eventos=total_eventos,
        total_tareas=total_tareas,
        tareas_completadas=tareas_completadas,
        porcentaje_global=porcentaje_global,
        eventos=EVENTOS
    )

# ==============================================================
# RUTAS HTML - Lista de eventos
# ==============================================================

@app.route('/eventos/')
def lista_eventos():
    """Lista todos los eventos con su progreso"""
    eventos_con_progreso = [obtener_evento_con_progreso(e) for e in EVENTOS]
    return render_template('lista_eventos.html',
        titulo='Eventos',
        eventos=eventos_con_progreso
    )

# ==============================================================
# RUTAS API - GET /api/eventos/
# ==============================================================

@app.route('/api/eventos/')
def api_lista_eventos():
    """API: Listar todos los eventos con porcentaje de avance"""
    eventos_con_progreso = [obtener_evento_con_progreso(e) for e in EVENTOS]
    return jsonify({
        'total': len(eventos_con_progreso),
        'eventos': eventos_con_progreso
    })

# ==============================================================
# RUTAS API - GET /api/eventos/<id>/
# ==============================================================

@app.route('/api/eventos/<int:id>/')
def api_detalle_evento(id):
    """API: Obtener un evento específico con sus tareas y porcentaje"""
    evento = next((e for e in EVENTOS if e['id'] == id), None)
    if evento is None:
        return jsonify({'error': 'Evento no encontrado', 'id': id}), 404
    
    tareas_evento = [t for t in TAREAS if t['evento_id'] == id]
    porcentaje = calcular_progreso(id)
    
    resultado = dict(evento)
    resultado['porcentaje_avance'] = porcentaje
    resultado['tareas'] = tareas_evento
    
    return jsonify(resultado)

# ==============================================================
# RUTAS API - GET /api/tareas/
# ==============================================================

@app.route('/api/tareas/')
def api_lista_tareas():
    """API: Listar todas las tareas"""
    return jsonify({
        'total': len(TAREAS),
        'tareas': TAREAS
    })

# ==============================================================
# MANEJO DE ERRORES
# ==============================================================

@app.errorhandler(404)
def pagina_no_encontrada(e):
    """Página 404 personalizada"""
    return render_template('404.html', titulo='Página no encontrada'), 404

# ==============================================================
# INICIO DEL SERVIDOR
# ==============================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)