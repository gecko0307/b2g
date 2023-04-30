# B2G: export Blender animation to GreenSock!

This is an experimental Blender 3.4 addon that lets you to save your actions as JavaScript animation code compatible with [GSAP 3](https://greensock.com/gsap/). It works by converting Blender keyframes to GSAP timeline methods such as `fromTo` and `to`.

For example, from this:

[![Screenshot](https://raw.githubusercontent.com/gecko0307/b2g/main/screenshot.png)](https://raw.githubusercontent.com/gecko0307/b2g/main/screenshot.png)

...you get this:

```javascript
tl.fromTo(data["Cube"], 1.0, { y: -3.0 }, { y: 3.0, ease: config.bezierEase(0.5384,0.6506,0.3718,1.7029) }, 0.0);
```

B2G outputs an ECMAScript module that can be plugged in to the project and used like this:

```javascript
import animation from "./blender-animation";

const tl = gsap.timeline({ repeat: -1, paused: true });
animation.create(tl, {});
tl.play(0);
```

B2G supports all interpolation/easing modes, such as Bezier, Quadratic, Cubic and others. Most of them are converted directly to GSAP's eases and work right out of the box on JS side, except Bezier and Constant. If you use them, you should provide the following configuration to `create` function:

```javascript
const config = {
    bezierEase: function(x1, y1, x2, y2) {
        return CustomEase.create(null, [x1, y1, x2, y2].join(","));
    },
    constantEase: function(x) {
        return (x < 1.0)? 0.0 : 1.0;
    }
};

const tl = gsap.timeline({ repeat: -1, paused: true });
animation.create(tl, config);
tl.play(0);
```

The code above requires [CustomEase](https://greensock.com/docs/v3/Eases/CustomEase) plugin.

B2G only animates object properties, it doesn't render your objects. In your rendering code (which can be based on canvas, WebGL, or a third-party graphics engine) you can use animated data exposed by B2G module in the following way:

```javascript
import animation from "./blender-animation";

function renderCube() {
    props = animation.data["Cube"];
    // Use props.x, props.y, props.z, props.rotationX, etc.
}
```

Keys in `animation.data` are Blender object names.
