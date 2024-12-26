#version 330

uniform vec3 wire_color;

out vec4 frag_color;

void main() { frag_color = vec4(wire_color, 1); }
