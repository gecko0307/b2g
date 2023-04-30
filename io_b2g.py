import bpy
import json
import os
import math
import mathutils
from mathutils import Vector, Matrix
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from bpy.types import Operator

bl_info = {
    'name': 'B2G',
    'description': 'Export animation to GSAP',
    'author': 'Timur Gafarov',
    'version': (1, 0),
    'blender': (3, 4, 0),
    'location': 'File > Import-Export',
    'warning': '',
    'wiki_url': '',
    'tracker_url': '',
    'support': 'COMMUNITY',
    'category': 'Import-Export'
}

interpolationToEaseFunc = {
    'CONSTANT': 'config.constantEase',
    'LINEAR': 'linear',
    'BEZIER': 'config.bezierEase',
    'SINE': 'sine.{mode}',
    'QUAD': 'power1.{mode}',
    'CUBIC': 'power2.{mode}',
    'QUART': 'power3.{mode}',
    'QUINT': 'power4.{mode}',
    'EXPO': 'expo.{mode}',
    'CIRC': 'circ.{mode}',
    'BACK': 'back.{mode}',
    'BOUNCE': 'bounce.{mode}',
    'ELASTIC': 'elastic.{mode}'
}

easingToGsapEaseMode = {
    'EASE_IN': 'in',
    'EASE_OUT': 'out',
    'EASE_IN_OUT': 'inOut'
}

def interpolationIsDynamicEffect(interpolation):
    if interpolation in ['BACK', 'BOUNCE', 'ELASTIC']:
        return True
    else:
        return False

def blenderEaseToGsapEase(interpolation, easing, back=1.0, amplitude=1.0, period=0.3, bezierPoints=[]):
    easeFunc = interpolationToEaseFunc[interpolation]
    if easing == 'AUTO':
        if interpolationIsDynamicEffect(interpolation):
            easing = 'EASE_OUT'
        else:
            easing = 'EASE_IN'
    easeMode = easingToGsapEaseMode[easing]
    ease = easeFunc.format(mode=easeMode)
    if interpolation == 'BACK':
        return '"%s(%s)"' % (ease, back)
    elif interpolation == 'BOUNCE':
        return '"%s"' % (ease)
    elif interpolation == 'ELASTIC':
        return '"%s(%s, %s)"' % (ease, amplitude, period)
    elif interpolation == 'BEZIER':
        return '%s(%s)' % (ease, ','.join(str(p) for p in bezierPoints))
    elif interpolation == 'CONSTANT':
        return ease
    else:
        return '"%s"' % ease

positionNames = ['x', 'y', 'z']
rotationNames = ['rotationX', 'rotationY', 'rotationZ']
scaleNames = ['scaleX', 'scaleY', 'scaleZ']

def exportMain(context, path, settings, operator):
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    playheadFrame = scene.frame_current
    scene.frame_set(0);
    
    data = {}
    tweensCode = ''
    
    for obj in scene.objects:
        if obj.animation_data == None:
            continue
        
        action = obj.animation_data.action
        
        objPosition = obj.matrix_world.to_translation()
        objScale = obj.matrix_world.to_scale()
        objRotation = obj.matrix_world.to_euler('XYZ')
        
        data[obj.name] = {
            'x': round(objPosition[0], 4),
            'y': round(objPosition[1], 4),
            'z': round(objPosition[2], 4),
            'rotationX': round(math.degrees(objRotation[0]), 4),
            'rotationY': round(math.degrees(objRotation[1]), 4),
            'rotationZ': round(math.degrees(objRotation[2]), 4),
            'scaleX': round(objScale[0], 4),
            'scaleY': round(objScale[1], 4),
            'scaleZ': round(objScale[2], 4)
        }
    
        isFirstTweenOfProperty = {
            'x': True,
            'y': True,
            'z': True,
            'rotationX': True,
            'rotationY': True,
            'rotationZ': True,
            'scaleX': True,
            'scaleY': True,
            'scaleZ': True
        }
        
        for fcurve in action.fcurves:
            propName = '_prop'
            print(fcurve.data_path)
            if fcurve.data_path == 'location':
                propName = positionNames[fcurve.array_index]
            elif fcurve.data_path == 'rotation_euler':
                propName = rotationNames[fcurve.array_index]
            elif fcurve.data_path == 'scale':
                propName = scaleNames[fcurve.array_index]
            else:
                continue
            firstKeyframe = True
            prevFrame = 0
            prevTime = 0
            prevValue = 0
            prevInterpolation = ''
            prevEasing = ''
            prevRightHandleFrame = 0
            prevRightHandleValue = 0
            prevBack = 0
            prevAmplitude = 0
            prevPeriod = 0
            for keyframe in fcurve.keyframe_points:
                frame = keyframe.co[0]
                time = frame / fps
                value = keyframe.co[1]
                leftHandleFrame = keyframe.handle_left[0]
                leftHandleValue = keyframe.handle_left[1]
                if not firstKeyframe:
                    timePos = round(prevTime, 4)
                    duration = round(time - prevTime, 4)
                    startValue = round(prevValue, 4)
                    endValue = round(value, 4)
                    if fcurve.data_path == 'rotation_euler':
                        startValue = round(math.degrees(startValue), 4)
                        endValue = round(math.degrees(endValue), 4)
                    bx1 = round(abs(prevRightHandleFrame - prevFrame) / abs(frame - prevFrame), 4)
                    by1 = round(abs(prevRightHandleValue - prevValue) / abs(value - prevValue), 4)
                    bx2 = round(abs(leftHandleFrame - prevFrame) / abs(frame - prevFrame), 4)
                    by2 = round(abs(leftHandleValue - prevValue) / abs(value - prevValue), 4)
                    gsapEase = blenderEaseToGsapEase(prevInterpolation, prevEasing,
                        back=round(prevBack, 4),
                        amplitude=round(prevAmplitude / abs(value - prevValue), 4),
                        period=round(prevPeriod / fps, 4),
                        bezierPoints=[bx1, by1, bx2, by2])
                    startObj = '{ %s: %s }' % (propName, startValue)
                    endObj = '{ %s: %s, ease: %s }' % (propName, endValue, gsapEase)
                    if isFirstTweenOfProperty[propName]:
                        tweensCode += '\ttl.fromTo(data["%s"], %s, %s, %s, %s);\n' % (obj.name, duration, startObj, endObj, timePos)
                        isFirstTweenOfProperty[propName] = False
                    else:
                        tweensCode += '\ttl.to(data["%s"], %s, %s, %s);\n' % (obj.name, duration, endObj, timePos)
                prevFrame = keyframe.co[0]
                prevTime = time
                prevValue = value
                prevInterpolation = keyframe.interpolation
                prevEasing = keyframe.easing
                prevRightHandleFrame = keyframe.handle_right[0]
                prevRightHandleValue = keyframe.handle_right[1]
                prevBack = keyframe.back
                prevAmplitude = keyframe.amplitude
                prevPeriod = keyframe.period
                firstKeyframe = False
    
    dataCode = 'const data = %s;\n\n' % json.dumps(data, indent=4)
    timelineFuncCode = 'function create(tl, config) {\n%s}\n\n' % (tweensCode)
    exportCode = 'export default {\n\tdata, create\n};\n'
    code = dataCode + timelineFuncCode + exportCode
    
    with open(path, 'w') as file:
        file.write(code)
    
    scene.frame_set(playheadFrame);
    
    return {'FINISHED'}

class GSAPExporter(Operator, ExportHelper):
    bl_idname = 'gecko0307.b2g'
    bl_label = 'Export GSAP animation'

    filename_ext = '.js'

    filter_glob: StringProperty(
        default='*.js',
        options={'HIDDEN'},
        maxlen=255, # Max internal buffer length, longer would be clamped.
    )
    
    def execute(self, context):
        settings = {
            
        }
        return exportMain(context, self.filepath, settings, self)

def menuFuncExport(self, context):
    self.layout.operator(GSAPExporter.bl_idname, text='GSAP timeline')

def register():
    bpy.utils.register_class(GSAPExporter)
    bpy.types.TOPBAR_MT_file_export.append(menuFuncExport)

def unregister():
    bpy.utils.unregister_class(GSAPExporter)
    bpy.types.TOPBAR_MT_file_export.remove(menuFuncExport)

if __name__ == '__main__':
    register()
