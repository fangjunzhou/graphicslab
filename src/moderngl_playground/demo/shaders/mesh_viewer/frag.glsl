#version 330

in vec4 vert_norm_world;
in vec4 vert_color;

uniform mat4 mat_MV;
uniform mat4 mat_P;
uniform mat4 mat_MVP;

out vec4 frag_color;

void main() { frag_color = (vert_norm_world + 1) / 2; }
